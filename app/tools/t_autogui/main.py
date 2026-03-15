"""Entry point for the GUI Agent system."""
import sys
import argparse
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging

logger = setup_logging("main")


def main():
    parser = argparse.ArgumentParser(description="GUI 自动化代理系统")
    parser.add_argument(
        "--mode",
        choices=["ui", "cli"],
        default="ui",
        help="运行模式: ui (Streamlit界面) 或 cli (命令行)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default="",
        help="CLI 模式下要执行的任务指令",
    )
    args = parser.parse_args()

    if args.mode == "ui":
        import subprocess
        ui_path = Path(__file__).parent / "ui" / "app.py"
        logger.info("Starting Streamlit UI...")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(ui_path),
            "--server.headless", "true",
        ])
    elif args.mode == "cli":
        if not args.task:
            print("请使用 --task 参数指定任务，例如：")
            print('  python main.py --mode cli --task "打开 Safari"')
            sys.exit(1)

        from agent.react_agent import ReactAgent

        agent = ReactAgent()
        logger.info(f"CLI mode - Task: {args.task}")

        def on_step(record):
            status = "✅" if record.success else "❌"
            action_type = record.action.type if hasattr(record.action, 'type') else "unknown"
            print(f"  {status} 步骤 {record.step_number}: [{action_type}] {record.thought[:80]}")

        print(f"\n🤖 开始执行任务: {args.task}\n")
        history = agent.run(args.task, callback=on_step)

        if agent.is_finished:
            print(f"\n✅ 任务完成: {agent.finish_message}")
        else:
            print(f"\n⚠️ 任务未完成，共执行 {len(history)} 步")


if __name__ == "__main__":
    main()
