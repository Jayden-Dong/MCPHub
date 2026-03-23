"""ReAct (Reasoning + Acting) loop agent for GUI automation."""
import time
from typing import Optional
from pathlib import Path

from PIL import Image

from ..config import setup_logging, MAX_STEPS, SCREENSHOT_DELAY, LOG_DIR
from ..schemas.actions import FinishedAction, WaitAction, StepRecord, LLMResponse
from ..llm.client import LLMClient
from ..tools.gui_tools import GUITools

logger = setup_logging("agent")


class ReactAgent:
    """Agent that executes GUI tasks using the ReAct loop pattern.

    Flow: Screenshot -> LLM Analysis -> Action Decision -> Execute -> Repeat
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        gui_tools: Optional[GUITools] = None,
        max_steps: int = MAX_STEPS,
        screenshot_delay: float = SCREENSHOT_DELAY,
    ):
        self.llm = llm_client or LLMClient()
        self.tools = gui_tools or GUITools()
        self.max_steps = max_steps
        self.screenshot_delay = screenshot_delay

        # Task state
        self.task: str = ""
        self.current_step: int = 0
        self.history: list[StepRecord] = []
        self.is_running: bool = False
        self.is_finished: bool = False
        self.finish_message: str = ""
        self.error_message: str = ""
        self.user_data: dict = {}
        self.start_time: Optional[float] = None

        # Screenshot storage directory
        self.screenshot_dir = LOG_DIR / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)

        logger.info(f"ReactAgent initialized: max_steps={max_steps}")

    def reset(self):
        """Reset agent state for a new task."""
        self.task = ""
        self.current_step = 0
        self.history.clear()
        self.is_running = False
        self.is_finished = False
        self.finish_message = ""
        self.error_message = ""
        self.user_data = {}
        self.start_time = None
        self.llm.reset()
        logger.info("Agent state reset")

    def _save_screenshot(self, screenshot: Image.Image, step: int) -> str:
        """Save a screenshot to disk and return the file path.

        Args:
            screenshot: PIL Image to save
            step: Current step number

        Returns:
            File path string
        """
        path = self.screenshot_dir / f"step_{step:03d}.png"
        screenshot.save(path)
        return str(path)

    def step(self, extra_context: str = "") -> StepRecord:
        """Execute a single ReAct step.

        Args:
            extra_context: Optional additional context for this step

        Returns:
            StepRecord with the result of this step
        """
        self.current_step += 1
        step_num = self.current_step
        step_start_time = time.time()

        logger.info(f"=== Step {step_num}/{self.max_steps} ===")

        # 1. Take screenshot
        screenshot = self.tools.take_screenshot()
        screenshot_path = self._save_screenshot(screenshot, step_num)

        # 2. Send to LLM for analysis and decision
        try:
            response: LLMResponse = self.llm.chat(
                screenshot=screenshot,
                task=self.task,
                step=step_num,
                max_steps=self.max_steps,
                extra_context=extra_context,
            )
        except ValueError as e:
            # LLM parse failure after retries
            step_duration = round(time.time() - step_start_time, 2)
            record = StepRecord(
                step_number=step_num,
                thought=f"LLM response parse failed: {e}",
                action=WaitAction(),
                success=False,
                error=str(e),
                screenshot_path=screenshot_path,
                duration=step_duration,
            )
            self.history.append(record)
            return record

        # 3. Check if task is finished
        if isinstance(response.action, FinishedAction):
            self.is_finished = True
            self.is_running = False
            self.finish_message = response.action.message
            self.user_data = response.action.user_data
            logger.info(f"Task completed: {self.finish_message}")

            step_duration = round(time.time() - step_start_time, 2)
            record = StepRecord(
                step_number=step_num,
                thought=response.thought,
                action=response.action,
                success=True,
                screenshot_path=screenshot_path,
                duration=step_duration,
            )
            self.history.append(record)
            return record

        # 4. Execute the action
        success = self.tools.execute_action(response.action)

        step_duration = round(time.time() - step_start_time, 2)
        record = StepRecord(
            step_number=step_num,
            thought=response.thought,
            action=response.action,
            success=success,
            error=None if success else "Action execution failed",
            screenshot_path=screenshot_path,
            duration=step_duration,
        )
        self.history.append(record)

        # 5. Wait for GUI to respond
        time.sleep(self.screenshot_delay)

        return record

    def run(self, task: str, callback=None) -> list[StepRecord]:
        """Run the full ReAct loop for a task.

        Args:
            task: Natural language task description
            callback: Optional callback function called after each step
                      with signature callback(step_record: StepRecord)

        Returns:
            List of StepRecords for all steps
        """
        self.reset()
        self.task = task
        self.is_running = True
        self.start_time = time.time()

        logger.info(f"Starting task: {task}")

        while self.is_running and self.current_step < self.max_steps:
            # Build extra context from previous step if it failed
            extra_context = ""
            if self.history and not self.history[-1].success:
                extra_context = f"上一步操作失败：{self.history[-1].error}"

            step_start_time = time.time()
            try:
                record = self.step(extra_context=extra_context)
            except Exception as e:
                logger.error(f"Step failed with exception: {e}")
                step_duration = round(time.time() - step_start_time, 2)
                record = StepRecord(
                    step_number=self.current_step,
                    thought=f"Exception occurred: {e}",
                    action=WaitAction(),
                    success=False,
                    error=str(e),
                    duration=step_duration,
                )
                self.history.append(record)

            # Notify callback
            if callback:
                callback(record)

            # Check termination conditions
            if self.is_finished:
                break

        if not self.is_finished and self.current_step >= self.max_steps:
            logger.warning(f"Task terminated: reached max steps ({self.max_steps})")
            self.is_running = False
            self.error_message = f"Task terminated: reached max steps ({self.max_steps})"

        return self.history

    def get_status(self) -> dict:
        """Get current agent status.

        Returns:
            Dict with task info, progress, and status
        """
        # Calculate elapsed time
        elapsed_seconds = 0.0
        if self.start_time is not None:
            elapsed_seconds = round(time.time() - self.start_time, 2)

        return {
            "task": self.task,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "is_running": self.is_running,
            "is_finished": self.is_finished,
            "finish_message": self.finish_message,
            "error_message": self.error_message,
            "user_data": self.user_data,
            "total_steps": len(self.history),
            "elapsed_seconds": elapsed_seconds,
        }
