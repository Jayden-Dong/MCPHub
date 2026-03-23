#!/usr/bin/env python3
"""
收集阈值预测模块

整合三种预测器:
- UDB 预测器：根据观测数据预测收集阈值
- AtoPlex 预测器：根据碱基序列和纯化方法预测收集阈值
- Degenerate 预测器：根据碱基序列、纯化方法、进样体积预测收集阈值

使用方法:
    from threshold_predictor import UDBPredictor, AtoPlexPredictor, DegeneratePredictor

    # UDB 预测
    predictor = UDBPredictor()
    raw, rounded = predictor.predict(seq, obs_threshold, obs_purity, obs_volume, desired_purity)

    # AtoPlex 预测
    predictor = AtoPlexPredictor()
    threshold = predictor.predict(sequence, purification_method)

    # Degenerate 预测
    predictor = DegeneratePredictor()
    threshold = predictor.predict(sequence, purification_method, injection_volume)
"""

import os
import pandas as pd
import numpy as np
import joblib
from typing import Optional, Tuple, Dict, Any, Annotated
from pydantic import Field


# 获取当前模块所在目录
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# UDB 预测器
# ============================================================================

DINUCS = ["AA", "AT", "AG", "AC", "TA", "TT", "TG", "TC",
          "GA", "GT", "GG", "GC", "CA", "CT", "CG", "CC"]


def _sequence_features_udb(seq: str) -> dict:
    """提取 UDB 预测器所需的序列特征"""
    seq = seq.upper().strip()
    n = len(seq)
    if n == 0:
        raise ValueError("碱基序列不能为空")

    a = seq.count("A")
    t = seq.count("T")
    g = seq.count("G")
    c = seq.count("C")
    gc = g + c
    at = a + t

    if n <= 14:
        tm = 2 * at + 4 * gc
    else:
        tm = 64.9 + 41.0 * (gc - 16.4) / n

    feats = {
        "seq_length": n,
        "gc_content": gc / n,
        "a_frac": a / n,
        "t_frac": t / n,
        "g_frac": g / n,
        "c_frac": c / n,
        "pur_pyr_ratio": (a + g) / max(at + gc, 1),
        "tm": tm,
    }
    for d in DINUCS:
        feats[f"dinuc_{d}"] = seq.count(d) / max(n - 1, 1)
    return feats


class UDBPredictor:
    """
    UDB 收集阈值预测器

    根据观测数据 (阈值、纯度、体积、目标纯度) 预测收集阈值
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        初始化预测器

        Args:
            model_path: 模型文件路径，默认为 udb_model.joblib
        """
        self.model_path = model_path or os.path.join(_MODULE_DIR, "udb_model.joblib")
        self._bundle = None
        self._model = None
        self._feature_cols = None

    def _load_model(self):
        """延迟加载模型"""
        if self._bundle is None:
            self._bundle = joblib.load(self.model_path)
            self._model = self._bundle["model"]
            self._feature_cols = self._bundle["feature_cols"]

    def predict(self,
                seq: str,
                obs_threshold: float,
                obs_purity: float,
                obs_volume: int,
                desired_purity: float) -> Tuple[float, float]:
        """
        预测收集阈值

        Args:
            seq: 碱基序列（5'→3'，仅含 A/T/G/C）
            obs_threshold: 当前已知的收集阈值（uV）
            obs_purity: 在该阈值下测得的 QC 纯度（%）
            obs_volume: 在该阈值下的馏分体积（0 或 1）
            desired_purity: 要求达到的目标纯度（%）

        Returns:
            (原始预测值，四舍五入后的预测值) - 单位：uV
        """
        self._load_model()

        seq_feats = _sequence_features_udb(seq)

        row = {
            "obs_threshold": obs_threshold,
            "obs_purity": obs_purity,
            "obs_volume": obs_volume,
            "desired_purity": desired_purity,
            **seq_feats,
        }

        X = np.array([[row[col] for col in self._feature_cols]])
        pred = self._model.predict(X)[0]

        # 将预测值对齐到最近的 5000 uV 档
        STEP = 5000
        pred_rounded = round(pred / STEP) * STEP

        return pred, pred_rounded


# ============================================================================
# AtoPlex 预测器
# ============================================================================

# AtoPlex 纯化方法映射表
ATOPLEX_METHOD_ALIASES = {
    # 序号输入
    '1': '短链纯化 -12min-1cm-V0.1',
    '2': '短链纯化 -19min-1cm-V0.1-兼并',
    '3': '短链纯化 -19min-1cm-V0.2-兼并',

    # 简化名称
    'v0.1': '短链纯化 -12min-1cm-V0.1',
    'v0.1-兼并': '短链纯化 -19min-1cm-V0.1-兼并',
    'v0.2-兼并': '短链纯化 -19min-1cm-V0.2-兼并',

    # 更简化的别名
    '普通': '短链纯化 -12min-1cm-V0.1',
    '兼并 1': '短链纯化 -19min-1cm-V0.1-兼并',
    '兼并 2': '短链纯化 -19min-1cm-V0.2-兼并',

    # 完整名称（直接匹配）
    '短链纯化 -12min-1cm-V0.1': '短链纯化 -12min-1cm-V0.1',
    '短链纯化 -19min-1cm-V0.1-兼并': '短链纯化 -19min-1cm-V0.1-兼并',
    '短链纯化 -19min-1cm-V0.2-兼并': '短链纯化 -19min-1cm-V0.2-兼并',
}


def _extract_sequence_features_atoplex(sequence: str) -> dict:
    """提取 AtoPlex 预测器所需的序列特征"""
    sequence = sequence.upper()
    features = {}
    total_bases = len(sequence)

    # 序列长度
    features['seq_length'] = len(sequence)

    # 主要碱基频率
    for base in 'ATCG':
        features[f'freq_{base}'] = sequence.count(base) / total_bases if total_bases > 0 else 0

    # GC 含量
    g_count = sequence.count('G')
    c_count = sequence.count('C')
    atcg_total = g_count + c_count + sequence.count('A') + sequence.count('T')
    features['gc_content'] = (g_count + c_count) / atcg_total if atcg_total > 0 else 0

    # 兼并碱基比例
    degenerate_bases = set('NRYSWKMBDHV')
    degenerate_count = sum(1 for base in sequence if base in degenerate_bases)
    features['degenerate_ratio'] = degenerate_count / total_bases if total_bases > 0 else 0

    return features


def _round_to_ten_thousand(value):
    """将数值四舍五入到万级别"""
    if isinstance(value, np.ndarray):
        return np.round(value / 10000) * 10000
    else:
        return round(value / 10000) * 10000


class AtoPlexPredictor:
    """
    AtoPlex 收集阈值预测器

    根据碱基序列和纯化方法预测收集阈值
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        初始化预测器

        Args:
            model_path: 模型文件路径，默认为 atoplex_model.joblib
        """
        self.model_path = model_path or os.path.join(_MODULE_DIR, "atoplex_model.joblib")
        self._model_data = None
        self._model = None
        self._scaler = None
        self._label_encoder = None
        self._feature_names = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model_data is None:
            self._model_data = joblib.load(self.model_path)
            self._model = self._model_data['model']
            self._scaler = self._model_data['scaler']
            self._label_encoder = self._model_data['label_encoder']
            self._feature_names = self._model_data['feature_names']

    def _normalize_method(self, method_input: str) -> Optional[str]:
        """将用户输入转换为标准纯化方法名称"""
        if method_input is None:
            return None

        method_input = method_input.strip()

        # 直接在映射表中查找
        if method_input in ATOPLEX_METHOD_ALIASES:
            return ATOPLEX_METHOD_ALIASES[method_input]

        # 尝试小写匹配
        method_lower = method_input.lower()
        for key, value in ATOPLEX_METHOD_ALIASES.items():
            if key.lower() == method_lower:
                return value

        # 检查是否是有效的完整名称
        if method_input in self._label_encoder.classes_:
            return method_input

        return None

    def get_supported_methods(self) -> Dict[str, str]:
        """获取支持的纯化方法列表"""
        return {
            '1': '短链纯化 -12min-1cm-V0.1',
            '2': '短链纯化 -19min-1cm-V0.1-兼并',
            '3': '短链纯化 -19min-1cm-V0.2-兼并',
        }

    def predict(self, sequence: str, purification_method: str) -> Optional[float]:
        """
        预测收集阈值

        Args:
            sequence: 碱基序列
            purification_method: 纯化方法（序号/别名/简称/完整名称）

        Returns:
            预测的收集阈值（四舍五入到万），如果输入无效返回 None
        """
        self._load_model()

        # 标准化纯化方法名称
        method_normalized = self._normalize_method(purification_method)

        if method_normalized is None:
            return None

        # 编码纯化方法
        method_encoded = self._label_encoder.transform([method_normalized])[0]

        # 准备特征
        features = _extract_sequence_features_atoplex(sequence)
        features['base_count'] = len(sequence)
        features['purification_method'] = method_encoded

        X = np.array([[features.get(name, 0) for name in self._feature_names]])
        X_scaled = self._scaler.transform(X)

        # 预测
        prediction = self._model.predict(X_scaled)[0]

        return _round_to_ten_thousand(prediction)

    def predict_batch(self, sequences: list, methods: list) -> list:
        """
        批量预测

        Args:
            sequences: 碱基序列列表
            methods: 纯化方法列表

        Returns:
            预测值列表
        """
        results = []
        for seq, method in zip(sequences, methods):
            pred = self.predict(seq, method)
            results.append(pred)
        return results


# ============================================================================
# Degenerate 预测器
# ============================================================================

# Degenerate 纯化方法映射表
DEGENERATE_PURIFICATION_METHODS = {
    1: "短链纯化 -16min-1cm-V0.1",
    2: "短链纯化 -16min-1cm-V0.2",
}


def _extract_sequence_features_degenerate(sequence: str) -> dict:
    """提取 Degenerate 预测器所需的序列特征"""
    features = {}

    # 序列长度
    features['seq_length'] = len(sequence)

    # 各碱基比例
    for base in ['A', 'T', 'C', 'G']:
        features[f'{base}_ratio'] = sequence.count(base) / len(sequence)

    # GC 含量
    features['gc_content'] = (sequence.count('G') + sequence.count('C')) / len(sequence)

    # AT 含量
    features['at_content'] = (sequence.count('A') + sequence.count('T')) / len(sequence)

    # 连续相同碱基的最大长度
    max_repeat = 1
    current_repeat = 1
    for i in range(1, len(sequence)):
        if sequence[i] == sequence[i-1]:
            current_repeat += 1
            max_repeat = max(max_repeat, current_repeat)
        else:
            current_repeat = 1
    features['max_repeat'] = max_repeat

    # 二联体特征（dinucleotide）
    dinucleotides = ['AA', 'AT', 'AC', 'AG', 'TA', 'TT', 'TC', 'TG',
                     'CA', 'CT', 'CC', 'CG', 'GA', 'GT', 'GC', 'GG']
    for di in dinucleotides:
        count = 0
        for i in range(len(sequence) - 1):
            if sequence[i:i+2] == di:
                count += 1
        features[f'di_{di}'] = count / (len(sequence) - 1) if len(sequence) > 1 else 0

    return features


def _prepare_features_degenerate(sequence: str, purification_method: str,
                                  injection_volume: Optional[float] = None) -> pd.DataFrame:
    """为 Degenerate 预测准备特征"""
    features = _extract_sequence_features_degenerate(sequence)

    # 添加碱基数量
    features['base_count'] = len(sequence)

    # 添加进样体积
    if injection_volume is not None:
        features['injection_volume'] = injection_volume
    else:
        features['injection_volume'] = 260  # 默认值

    # 添加纯化方法
    features['purification_method'] = purification_method

    return pd.DataFrame([features])


def _round_to_wan(value):
    """将数值四舍五入到万级别"""
    return round(value / 10000) * 10000


class DegeneratePredictor:
    """
    Degenerate 收集阈值预测器

    根据碱基序列、纯化方法、进样体积预测收集阈值
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        初始化预测器

        Args:
            model_path: 模型文件路径，默认为 degenerate_model.joblib
        """
        self.model_path = model_path or os.path.join(_MODULE_DIR, "degenerate_model.joblib")
        self._model_data = None
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model_data is None:
            self._model_data = joblib.load(self.model_path)
            self._model = self._model_data['model']

    def get_supported_methods(self) -> Dict[int, str]:
        """获取支持的纯化方法列表"""
        return DEGENERATE_PURIFICATION_METHODS.copy()

    def _resolve_purification_method(self, method_input) -> str:
        """解析纯化方法输入（支持数字或文字）"""
        # 尝试解析为数字
        try:
            method_num = int(method_input)
            if method_num in DEGENERATE_PURIFICATION_METHODS:
                return DEGENERATE_PURIFICATION_METHODS[method_num]
            else:
                raise ValueError(f"无效的纯化方法编号：{method_num}")
        except (ValueError, TypeError):
            # 不是数字，直接作为方法名称
            return method_input

    def predict(self,
                sequence: str,
                purification_method,
                injection_volume: Optional[float] = None) -> float:
        """
        预测收集阈值

        Args:
            sequence: 碱基序列
            purification_method: 纯化方法（数字或名称）
            injection_volume: 进样体积（可选，默认 260）

        Returns:
            预测的收集阈值（四舍五入到万）
        """
        self._load_model()

        # 标准化序列
        sequence = sequence.upper().strip()

        # 解析纯化方法
        purification_method = self._resolve_purification_method(purification_method)

        # 准备特征
        X = _prepare_features_degenerate(sequence, purification_method, injection_volume)

        # 预测
        prediction = self._model.predict(X)[0]

        return _round_to_wan(prediction)

    def predict_batch(self,
                      sequences: list,
                      methods: list,
                      injection_volumes: Optional[list] = None) -> list:
        """
        批量预测

        Args:
            sequences: 碱基序列列表
            methods: 纯化方法列表
            injection_volumes: 进样体积列表（可选）

        Returns:
            预测值列表
        """
        results = []
        if injection_volumes is None:
            injection_volumes = [None] * len(sequences)

        for seq, method, vol in zip(sequences, methods, injection_volumes):
            pred = self.predict(seq, method, vol)
            results.append(pred)
        return results


# ============================================================================
# 统一预测器（可选使用）
# ============================================================================

class ThresholdPredictor:
    """
    统一预测器接口

    提供对所有三种预测器的统一访问
    """

    def __init__(self,
                 udb_model_path: Optional[str] = None,
                 atoplex_model_path: Optional[str] = None,
                 degenerate_model_path: Optional[str] = None):
        """
        初始化统一预测器

        Args:
            udb_model_path: UDB 模型路径
            atoplex_model_path: AtoPlex 模型路径
            degenerate_model_path: Degenerate 模型路径
        """
        self._udb = None
        self._atoplex = None
        self._degenerate = None

        self._udb_model_path = udb_model_path
        self._atoplex_model_path = atoplex_model_path
        self._degenerate_model_path = degenerate_model_path

    @property
    def udb(self) -> UDBPredictor:
        """获取 UDB 预测器"""
        if self._udb is None:
            self._udb = UDBPredictor(self._udb_model_path)
        return self._udb

    @property
    def atoplex(self) -> AtoPlexPredictor:
        """获取 AtoPlex 预测器"""
        if self._atoplex is None:
            self._atoplex = AtoPlexPredictor(self._atoplex_model_path)
        return self._atoplex

    @property
    def degenerate(self) -> DegeneratePredictor:
        """获取 Degenerate 预测器"""
        if self._degenerate is None:
            self._degenerate = DegeneratePredictor(self._degenerate_model_path)
        return self._degenerate


# ============================================================================
# 便捷函数 (MCP 工具函数)
# ============================================================================

def predict_udb(
    seq: Annotated[str, Field(description="碱基序列（5'→3'，仅含 A/T/G/C）")],
    obs_threshold: Annotated[float, Field(description="当前已知的收集阈值（uV）")],
    obs_purity: Annotated[float, Field(description="在该阈值下测得的 QC 纯度（%）")],
    obs_volume: Annotated[int, Field(description="在该阈值下的馏分体积（0 或 1）")],
    desired_purity: Annotated[float, Field(description="要求达到的目标纯度（%）")],
    model_path: Annotated[Optional[str], Field(description="模型文件路径（可选，为空使用默认路径）")] = None
) -> Dict[str, Any]:
    """
    UDB 预测便捷函数 - 根据观测数据 (阈值、纯度、体积、目标纯度) 预测收集阈值
    
    Returns:
        包含 success 字段和预测结果的字典
    """
    try:
        predictor = UDBPredictor(model_path)
        raw, rounded = predictor.predict(seq, obs_threshold, obs_purity, obs_volume, desired_purity)
        return {
            "success": True,
            "raw_prediction": raw,
            "rounded_prediction": rounded,
            "unit": "uV"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def predict_atoplex(
    sequence: Annotated[str, Field(description="碱基序列")],
    purification_method: Annotated[str, Field(description="纯化方法（序号/别名/简称/完整名称），支持：1/普通/v0.1=短链纯化 -12min-1cm-V0.1, 2/兼并 1/v0.1-兼并=短链纯化 -19min-1cm-V0.1-兼并，3/兼并 2/v0.2-兼并=短链纯化 -19min-1cm-V0.2-兼并")],
    model_path: Annotated[Optional[str], Field(description="模型文件路径（可选，为空使用默认路径）")] = None
) -> Dict[str, Any]:
    """
    AtoPlex 预测便捷函数 - 根据碱基序列和纯化方法预测收集阈值
    
    Returns:
        包含 success 字段和预测结果的字典
    """
    try:
        predictor = AtoPlexPredictor(model_path)
        pred = predictor.predict(sequence, purification_method)
        if pred is not None:
            return {
                "success": True,
                "prediction": pred,
                "unit": "uV"
            }
        else:
            return {
                "success": False,
                "error": "无效的纯化方法"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def predict_degenerate(
    sequence: Annotated[str, Field(description="碱基序列")],
    purification_method: Annotated[str, Field(description="纯化方法（数字或名称），支持：1=短链纯化 -16min-1cm-V0.1, 2=短链纯化 -16min-1cm-V0.2")],
    injection_volume: Annotated[Optional[float], Field(description="进样体积（可选，默认 260）")] = None,
    model_path: Annotated[Optional[str], Field(description="模型文件路径（可选，为空使用默认路径）")] = None
) -> Dict[str, Any]:
    """
    Degenerate 预测便捷函数 - 根据碱基序列、纯化方法、进样体积预测收集阈值
    
    Returns:
        包含 success 字段和预测结果的字典
    """
    try:
        predictor = DegeneratePredictor(model_path)
        pred = predictor.predict(sequence, purification_method, injection_volume)
        return {
            "success": True,
            "prediction": pred,
            "unit": "uV"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# 命令行接口（保留原有交互功能）
# ============================================================================

def _interactive_udb():
    """UDB 交互式预测"""
    print("=" * 60)
    print("UDB 收集阈值预测")
    print("=" * 60)

    predictor = UDBPredictor()

    while True:
        print("\n请输入预测参数（输入 'q' 退出）:")

        seq = input("\n碱基序列：").strip().upper()
        if seq.lower() == 'q':
            break

        try:
            obs_threshold = float(input("观测阈值 (uV): ").strip())
            obs_purity = float(input("观测纯度 (%): ").strip())
            obs_volume = int(input("馏分体积 (0 或 1): ").strip())
            desired_purity = float(input("目标纯度 (%): ").strip())
        except ValueError:
            print("错误：请输入有效的数值")
            continue

        try:
            raw, rounded = predictor.predict(seq, obs_threshold, obs_purity, obs_volume, desired_purity)
            print(f"\n预测结果:")
            print(f"  原始预测：{raw:,.0f} uV")
            print(f"  取整预测：{rounded:,.0f} uV")
        except Exception as e:
            print(f"预测失败：{e}")


def _interactive_atoplex():
    """AtoPlex 交互式预测"""
    print("=" * 60)
    print("AtoPlex 收集阈值预测")
    print("=" * 60)

    predictor = AtoPlexPredictor()

    # 显示方法选择菜单
    print("\n纯化方法选择:")
    print("-" * 50)
    for num, name in predictor.get_supported_methods().items():
        print(f"  [{num}] {name}")
    print("-" * 50)

    while True:
        print("\n请输入预测参数（输入 'q' 退出）:")

        seq = input("\n碱基序列：").strip().upper()
        if seq.lower() == 'q':
            break

        method = input("纯化方法 (序号/别名): ").strip()
        if method.lower() == 'q':
            break

        pred = predictor.predict(seq, method)
        if pred is not None:
            print(f"\n预测收集阈值：{pred:.0f}")
        else:
            print("错误：无效的纯化方法")


def _interactive_degenerate():
    """Degenerate 交互式预测"""
    print("=" * 60)
    print("Degenerate 收集阈值预测")
    print("=" * 60)

    predictor = DegeneratePredictor()

    # 显示方法选择菜单
    print("\n纯化方法选择:")
    print("-" * 50)
    for num, name in predictor.get_supported_methods().items():
        print(f"  [{num}] {name}")
    print("-" * 50)

    while True:
        print("\n请输入预测参数（输入 'q' 退出）:")

        seq = input("\n碱基序列：").strip().upper()
        if seq.lower() == 'q':
            break

        method = input("纯化方法 (序号): ").strip()
        if method.lower() == 'q':
            break

        vol_input = input("进样体积 (可选，回车使用默认值 260): ").strip()
        vol = float(vol_input) if vol_input else None

        try:
            pred = predictor.predict(seq, method, vol)
            print(f"\n预测收集阈值：{pred:.0f}")
        except Exception as e:
            print(f"预测失败：{e}")


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("收集阈值预测系统")
    print("=" * 60)
    print("\n请选择预测器:")
    print("  [1] UDB 预测器")
    print("  [2] AtoPlex 预测器")
    print("  [3] Degenerate 预测器")
    print("  [q] 退出")

    choice = input("\n请输入选择：").strip().lower()

    if choice == '1':
        _interactive_udb()
    elif choice == '2':
        _interactive_atoplex()
    elif choice == '3':
        _interactive_degenerate()
    elif choice == 'q':
        print("退出系统")
    else:
        print("无效选择")
