# Logging configuration
import logging
import logging.handlers
import sys
from pathlib import Path
from config_py.config import settings

# 单例模式标志，确保日志系统只被初始化一次
_logging_initialized = False

def setup_logging():
    """设置日志配置（单例模式）"""
    global _logging_initialized
    
    # 如果已经初始化过，直接返回logger实例
    if _logging_initialized:
        return logging.getLogger(__name__)
    
    try:
        # 创建日志目录
        log_path = Path(settings.LOG_FILE)
        log_dir = log_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 创建文件处理器 - 按天轮转
        # 添加延迟到第一次写入时创建文件，避免启动时的文件锁定问题
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=settings.LOG_FILE,
            when='midnight',  # 每天午夜轮转
            interval=1,       # 每1天
            backupCount=settings.LOG_BACKUP_COUNT,  # 保留的备份文件数量
            encoding='utf-8',
            utc=False,  # 使用本地时间
            delay=True  # 延迟创建文件
        )
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y-%m-%d"  # 备份文件后缀格式

        # # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        root_logger.handlers.clear()  # 清除默认处理器
        root_logger.addHandler(file_handler)

        # 设置第三方库的日志级别
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("fastapi").setLevel(logging.INFO)

        # 标记为已初始化
        _logging_initialized = True
        
        logger = logging.getLogger(__name__)
        logger.info("日志系统初始化完成")
        logger.info(f"日志文件: {settings.LOG_FILE}")
        logger.info(f"日志轮转: 每天午夜轮转，保留 {settings.LOG_BACKUP_COUNT} 个备份文件")
        return logger
    except Exception as e:
        # 如果初始化失败，创建一个简单的控制台日志器作为回退
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.setLevel(logging.INFO)
        
        if not fallback_logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            fallback_logger.addHandler(console_handler)
        
        fallback_logger.error(f"日志系统初始化失败: {e}")
        fallback_logger.warning("使用控制台日志作为回退")
        return fallback_logger


def setup_mcp_logging():
    """设置访问日志配置，用于记录mcp请求"""
    # 创建访问日志文件路径
    mcp_log_file = Path(settings.MCP_LOG_FILE)
    access_log_dir = mcp_log_file.parent
    access_log_dir.mkdir(parents=True, exist_ok=True)

    # 创建访问日志格式化器（类似Apache/Nginx访问日志格式，包含线程号）
    mcp_formatter = logging.Formatter(
        '%(asctime)s - [%(thread)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建访问日志文件处理器 - 按天轮转
    mcp_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(mcp_log_file),
        when='midnight',  # 每天午夜轮转
        interval=1,  # 每1天
        backupCount=settings.MCP_LOG_BACKUP_COUNT,  # 保留的备份文件数量
        encoding='utf-8',
        utc=False  # 使用本地时间
    )
    mcp_file_handler.setFormatter(mcp_formatter)
    mcp_file_handler.suffix = "%Y-%m-%d"  # 备份文件后缀格式

    # 创建访问日志记录器
    mcp_logger = logging.getLogger(__name__)
    mcp_logger.setLevel(getattr(logging, settings.MCP_LOG_LEVEL.upper()))
    mcp_logger.handlers.clear()  # 清除默认处理器
    mcp_logger.addHandler(mcp_file_handler)
    mcp_logger.propagate = False  # 不传播到根日志器，避免重复记录

    mcp_logger.info("mcp日志系统初始化完成")
    mcp_logger.info(f"mcp日志文件: {settings.MCP_LOG_FILE}")
    mcp_logger.info(f"mcp日志轮转: 每天午夜轮转，保留 {settings.MCP_LOG_BACKUP_COUNT} 个备份文件")

    return mcp_logger

app_logger = setup_logging()
mcp_logger = setup_mcp_logging()