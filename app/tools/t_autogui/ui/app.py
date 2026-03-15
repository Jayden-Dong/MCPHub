"""Streamlit UI for the GUI Agent system."""
import streamlit as st
import time
from PIL import Image
from pathlib import Path

# Must set page config first
st.set_page_config(
    page_title="GUI 自动化代理",
    page_icon="🤖",
    layout="wide",
)

# Import after page config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import setup_logging, DASHSCOPE_API_KEY, MODEL_NAME, MAX_STEPS
from schemas.actions import StepRecord, FinishedAction
from llm.client import LLMClient
from tools.gui_tools import GUITools
from agent.react_agent import ReactAgent

logger = setup_logging("ui")


def init_session_state():
    """Initialize Streamlit session state variables."""
    defaults = {
        "agent": None,
        "history": [],
        "is_running": False,
        "should_stop": False,  # Flag to signal stop
        "task_input": "",
        "current_status": "就绪",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def handle_stop():
    """Handle stop button click."""
    logger.info("User clicked stop button - stopping task")
    st.session_state.should_stop = True
    st.session_state.is_running = False
    if st.session_state.agent:
        st.session_state.agent.is_running = False
        logger.info(f"Task stopped by user: {st.session_state.agent.task}")


def handle_clear_history():
    """Handle clear history button click."""
    st.session_state.history = []
    st.session_state.agent = None
    st.session_state.is_running = False
    st.session_state.should_stop = False
    st.session_state.task_input = ""


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.header("⚙️ 配置")

        # API status
        if DASHSCOPE_API_KEY:
            st.success("API Key 已配置")
        else:
            st.error("API Key 未配置，请在 .env 文件中设置 DASHSCOPE_API_KEY")

        st.text(f"模型: {MODEL_NAME}")

        # Agent parameters
        max_steps = st.slider(
            "最大步数",
            min_value=5,
            max_value=50,
            value=MAX_STEPS,
            step=5,
        )

        screenshot_delay = st.slider(
            "截屏间隔 (秒)",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
        )

        st.divider()
        st.header("📊 系统信息")

        if st.session_state.agent:
            status = st.session_state.agent.get_status()
            # Display friendly status
            if status.get("is_finished"):
                st.success(f"✅ 任务已完成: {status.get('task', '')}")
            elif status.get("is_running"):
                st.info(f"🔄 任务运行中: {status.get('task', '')} (第 {status.get('current_step', 0)}/{status.get('max_steps', 0)} 步)")
            else:
                st.warning(f"⏸️ 任务已停止")
            st.text(f"当前步数: {status.get('current_step', 0)} / {status.get('max_steps', 0)}")

        return max_steps, screenshot_delay


def render_step_card(record: StepRecord):
    """Render a single step as an expandable card."""
    action_type = record.action.type if hasattr(record.action, 'type') else str(record.action)
    status_icon = "✅" if record.success else "❌"

    # Build header with duration
    header = f"{status_icon} 步骤 {record.step_number} - {action_type}"
    if record.duration is not None:
        header += f" ({record.duration}秒)"

    with st.expander(
        header,
        expanded=(record.step_number == len(st.session_state.history)),
    ):
        # Thought
        st.markdown(f"**💭 推理：**")
        st.info(record.thought)

        # Action details
        st.markdown(f"**🎯 操作：**")
        if hasattr(record.action, 'model_dump'):
            st.json(record.action.model_dump())
        else:
            st.json(record.action)

        # Screenshot
        if record.screenshot_path and Path(record.screenshot_path).exists():
            st.markdown(f"**📸 截屏：**")
            st.image(record.screenshot_path, use_container_width=True)

        # Error
        if record.error:
            st.error(f"错误: {record.error}")


def render_current_step(record: StepRecord):
    """Render the current step prominently in the center."""
    st.subheader(f"🔄 当前步骤 {record.step_number}")
    render_step_card(record)
    st.divider()
    # Also show previous steps
    if len(st.session_state.history) > 1:
        with st.expander("📋 查看历史步骤"):
            for i, r in enumerate(st.session_state.history[:-1]):
                with st.expander(f"步骤 {r.step_number} - {r.action.type}"):
                    st.write(f"**推理**: {r.thought}")
                    st.json(r.action.model_dump() if hasattr(r.action, 'model_dump') else r.action)
                    if r.screenshot_path and Path(r.screenshot_path).exists():
                        st.image(r.screenshot_path)


def render_history():
    """Render the execution history."""
    if not st.session_state.history:
        st.info("暂无执行记录。请输入任务并点击开始。")
        return

    is_running = st.session_state.get("is_running", False)
    # Always expand history while running
    with st.expander(f"📋 执行历史 ({len(st.session_state.history)} 步)", expanded=is_running):
        for i, record in enumerate(st.session_state.history):
            render_step_card(record)


def main():
    """Main Streamlit app."""
    init_session_state()

    st.title("🤖 GUI 自动化代理系统")
    st.caption("基于视觉语言模型的智能桌面自动化工具")

    # Sidebar
    max_steps, screenshot_delay = render_sidebar()

    # Sync session state with agent state
    agent = st.session_state.agent
    if agent:
        status = agent.get_status()
        # If agent is not running (finished or stopped), sync session state
        if not status.get("is_running", False):
            st.session_state.is_running = False

    # Main area
    task = st.text_area(
        "📝 输入任务指令",
        placeholder="例如：打开浏览器，搜索「今天天气」",
        height=68,
    )

    # Buttons in one row
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
    with btn_col1:
        start_btn = st.button(
            "▶️ 开始执行",
            disabled=not task or not DASHSCOPE_API_KEY or st.session_state.is_running,
            use_container_width=True,
            type="primary",
        )
    with btn_col2:
        stop_btn = st.button(
            "⏹️ 停止",
            disabled=not st.session_state.is_running,
            use_container_width=True,
            on_click=handle_stop,
        )
    with btn_col3:
        clear_btn = st.button(
            "🗑️ 清空历史",
            disabled=st.session_state.is_running,
            use_container_width=True,
            on_click=handle_clear_history,
        )

    st.divider()

    # Status bar
    status_container = st.empty()

    # Continue running task if agent is active
    agent = st.session_state.agent
    if st.session_state.is_running and agent and agent.is_running:
        try:
            # Check if stop was requested
            if st.session_state.should_stop:
                status_container.warning("⏹️ 任务已被用户停止")
                agent.is_running = False
                st.session_state.is_running = False
                render_history()
            else:
                status_container.info(f"🔄 正在执行任务: {agent.task}")

                # Execute one step
                extra_context = ""
                if agent.history and not agent.history[-1].success:
                    extra_context = f"上一步操作失败：{agent.history[-1].error}"

                record = agent.step(extra_context=extra_context)
                st.session_state.history.append(record)

                # Show current step prominently in the center
                render_current_step(record)

                if agent.is_finished:
                    status_container.success(f"✅ 任务完成: {agent.finish_message}")
                    agent.is_running = False
                    st.session_state.is_running = False
                    st.rerun()
                elif agent.current_step >= agent.max_steps:
                    status_container.warning(f"⚠️ 任务未完成，已达到最大步数 ({max_steps})")
                    agent.is_running = False
                    st.session_state.is_running = False
                else:
                    # Continue in next render cycle to allow button interaction
                    time.sleep(1)
                    st.rerun()

        except Exception as e:
            status_container.error(f"❌ 执行出错: {e}")
            logger.error(f"Task execution error: {e}", exc_info=True)
            st.session_state.is_running = False

    # Execute new task
    if start_btn and task and not st.session_state.is_running:
        st.session_state.history = []
        st.session_state.should_stop = False
        st.session_state.is_running = True

        try:
            agent = ReactAgent(
                max_steps=max_steps,
                screenshot_delay=screenshot_delay,
            )
            st.session_state.agent = agent
            agent.task = task
            agent.is_running = True
            status_container.info(f"🔄 正在执行任务: {task}")

            # Execute first step
            record = agent.step(extra_context="")
            st.session_state.history.append(record)

            # Show current step prominently in the center
            render_current_step(record)

            # Check if finished immediately
            if agent.is_finished:
                status_container.success(f"✅ 任务完成: {agent.finish_message}")
                st.session_state.is_running = False
                st.rerun()
            elif agent.current_step >= agent.max_steps:
                status_container.warning(f"⚠️ 任务未完成，已达到最大步数 ({max_steps})")
                st.session_state.is_running = False
            else:
                # Continue in next render cycle
                time.sleep(1)
                st.rerun()

        except Exception as e:
            status_container.error(f"❌ 执行出错: {e}")
            logger.error(f"Task execution error: {e}", exc_info=True)
            st.session_state.is_running = False

    # Show history
    render_history()


if __name__ == "__main__":
    main()
