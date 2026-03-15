"""GUI automation tools wrapping PyAutoGUI for cross-platform support."""
import time

import pyautogui
from PIL import Image

from ..config import setup_logging, SCREENSHOT_DELAY
from ..platform.factory import get_platform_adapter
from ..schemas.actions import (
    ActionType,
    ClickAction,
    TypeAction,
    HotkeyAction,
    ScrollAction,
    DragAction,
    WaitAction,
    FinishedAction,
)

logger = setup_logging("tools")

# PyAutoGUI safety settings
pyautogui.FAILSAFE = True   # Move mouse to corner to abort
pyautogui.PAUSE = 0.3       # Brief pause between actions


class GUITools:
    """Wrapper for GUI automation operations with logging and safety.

    This class provides cross-platform GUI automation through platform adapters
    that handle OS-specific differences in keyboard shortcuts and clipboard operations.
    """

    def __init__(self):
        # Get platform adapter for OS-specific operations
        self.platform = get_platform_adapter()
        platform_info = self.platform.info

        # Get screen size for boundary checking
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(
            f"GUITools initialized. "
            f"Platform: {platform_info.name}, "
            f"Screen: {self.screen_width}x{self.screen_height}, "
            f"Modifier: {platform_info.modifier_display}"
        )

    def take_screenshot(self) -> Image.Image:
        """Capture the current screen.

        Uses pyautogui.screenshot() for cross-platform support.

        Returns:
            PIL Image of the current screen
        """
        logger.info("Taking screenshot...")

        # Use pyautogui for cross-platform screenshot
        screenshot = pyautogui.screenshot()
        logger.info(f"Screenshot captured: {screenshot.size}")
        return screenshot

    def _convert_relative_coords(self, x: float, y: float) -> tuple[int, int]:
        """Convert relative coordinates (0-1) to absolute pixel coordinates.

        Args:
            x: Relative x coordinate [0, 1) or absolute pixel value
            y: Relative y coordinate [0, 1) or absolute pixel value

        Returns:
            Tuple of (absolute_x, absolute_y) in pixels
        """
        # Check if coordinates are relative (0-1 range) or absolute (pixel values)
        # If coordinates are greater than 1, treat them as absolute pixel values
        if x > 1.0 or y > 1.0:
            # Assume absolute coordinates
            return int(x), int(y)

        # Convert relative coordinates to absolute pixels
        absolute_x = int(x * self.screen_width)
        absolute_y = int(y * self.screen_height)

        # Clamp to valid screen bounds
        absolute_x = max(0, min(absolute_x, self.screen_width - 1))
        absolute_y = max(0, min(absolute_y, self.screen_height - 1))

        return absolute_x, absolute_y

    def _validate_coordinates(self, x: int, y: int) -> bool:
        """Check if coordinates are within screen bounds.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if coordinates are valid
        """
        if 0 <= x < self.screen_width and 0 <= y < self.screen_height:
            return True
        logger.warning(
            f"Coordinates ({x}, {y}) out of bounds. "
            f"Screen: {self.screen_width}x{self.screen_height}"
        )
        return False

    def click(self, action: ClickAction) -> bool:
        """Execute a mouse click action.

        Args:
            action: ClickAction with coordinates (relative or absolute) and button info

        Returns:
            True if successful
        """
        # Convert relative coordinates to absolute if needed
        x, y = self._convert_relative_coords(action.x, action.y)

        if not self._validate_coordinates(x, y):
            return False

        try:
            logger.info(
                f"Click: ({x}, {y}) [original: ({action.x}, {action.y})] "
                f"button={action.button} clicks={action.clicks}"
            )
            pyautogui.click(
                x=x,
                y=y,
                button=action.button,
                clicks=action.clicks,
            )
            return True
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False

    def type_text(self, action: TypeAction, clear_first: bool = False) -> bool:
        """Execute a text input action.

        Uses platform-adapted clipboard operations for reliable text input
        (supports Chinese and other Unicode characters).

        Args:
            action: TypeAction with text to type
            clear_first: If True, select all and delete before typing

        Returns:
            True if successful
        """
        try:
            text = action.text
            logger.info(f"Type: '{text[:50]}{'...' if len(text) > 50 else ''}'")

            # Optionally clear existing content first using platform-adapted hotkey
            if clear_first:
                select_keys, delete_key = self.platform.get_clear_input_sequence()
                pyautogui.hotkey(*select_keys)
                time.sleep(0.1)
                pyautogui.press(delete_key)
                time.sleep(0.1)

            # Use platform-adapted clipboard operation
            if not self.platform.copy_to_clipboard(text):
                logger.error("Failed to copy text to clipboard")
                return False

            time.sleep(0.1)

            # Use platform-adapted paste hotkey
            pyautogui.hotkey(*self.platform.info.paste_keys)
            time.sleep(0.2)  # Wait for paste to complete
            return True
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False

    def hotkey(self, action: HotkeyAction) -> bool:
        """Execute a keyboard shortcut action.

        Args:
            action: HotkeyAction with key combination

        Returns:
            True if successful
        """
        try:
            keys = action.keys
            logger.info(f"Hotkey: {' + '.join(keys)}")
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return False

    def scroll(self, action: ScrollAction) -> bool:
        """Execute a scroll action with flexible scrolling.

        Args:
            action: ScrollAction with position (relative or absolute) and direction

        Returns:
            True if successful
        """
        # Convert relative coordinates to absolute if needed
        x, y = self._convert_relative_coords(action.x, action.y)

        if not self._validate_coordinates(x, y):
            return False

        try:
            # Determine scroll direction and amount
            is_up = action.direction == "up"
            scroll_amount = action.amount
            logger.info(
                f"Scroll: ({x}, {y}) [original: ({action.x}, {action.y})] "
                f"direction={action.direction} amount={action.amount}"
            )

            # Move mouse to scroll position first
            pyautogui.moveTo(x, y, duration=0.1)
            time.sleep(0.1)

            # Calculate scroll value - Windows pyautogui.scroll() needs larger values
            # Default multiplier is 10, can be adjusted
            scroll_unit = 100  # 每次滚动的单位值

            if scroll_amount <= 3:
                # Small scroll: multiple small scrolls
                for i in range(scroll_amount):
                    scroll_value = scroll_unit if is_up else -scroll_unit
                    logger.info(f"Scroll step {i+1}/{scroll_amount}: value={scroll_value}")
                    pyautogui.scroll(scroll_value)
                    time.sleep(0.05)
            else:
                # Large scroll (pagination): use scroll_amount as the direct value
                # e.g., scroll_amount=3000 means scroll 3000 units
                scroll_value = scroll_amount if is_up else -scroll_amount
                logger.info(f"Scrolling with value: {scroll_value}")
                pyautogui.scroll(scroll_value)

            # Wait for scroll to take effect
            time.sleep(0.3)

            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False

    def drag(self, action: DragAction) -> bool:
        """Execute a drag action to move files or elements.

        Args:
            action: DragAction with start and end coordinates

        Returns:
            True if successful
        """
        try:
            # Convert relative coordinates to absolute
            x1, y1 = self._convert_relative_coords(action.x1, action.y1)
            x2, y2 = self._convert_relative_coords(action.x2, action.y2)

            logger.info(
                f"Drag: ({x1}, {y1}) -> ({x2}, {y2}) "
                f"[original: ({action.x1}, {action.y1}) -> ({action.x2}, {action.y2})]"
            )

            # Perform drag operation
            # Move to start position
            pyautogui.moveTo(x1, y1, duration=0.2)
            time.sleep(0.1)

            # Mouse down, move to end position, mouse up
            pyautogui.mouseDown(button=action.button)
            time.sleep(0.1)
            pyautogui.moveTo(x2, y2, duration=0.5)
            time.sleep(0.1)
            pyautogui.mouseUp(button=action.button)

            # Wait for drag to complete
            time.sleep(0.3)

            return True
        except Exception as e:
            logger.error(f"Drag failed: {e}")
            return False

    def wait(self, action: WaitAction) -> bool:
        """Execute a wait action.

        Args:
            action: WaitAction with duration

        Returns:
            True always
        """
        logger.info(f"Wait: {action.seconds}s")
        time.sleep(action.seconds)
        return True

    def execute_action(self, action: ActionType) -> bool:
        """Execute any action type by dispatching to the appropriate method.

        Args:
            action: An action object (ClickAction, TypeAction, etc.)

        Returns:
            True if the action was executed successfully
        """
        action_map = {
            "click": self.click,
            "type": self.type_text,
            "hotkey": self.hotkey,
            "scroll": self.scroll,
            "drag": self.drag,
            "wait": self.wait,
        }

        if isinstance(action, FinishedAction):
            logger.info(f"Task finished: {action.message}")
            return True

        handler = action_map.get(action.type)
        if handler is None:
            logger.error(f"Unknown action type: {action.type}")
            return False

        return handler(action)

    def get_screen_info(self) -> dict:
        """Get current screen information.

        Returns:
            Dict with screen width, height, and mouse position
        """
        mouse_x, mouse_y = pyautogui.position()
        return {
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "mouse_x": mouse_x,
            "mouse_y": mouse_y,
        }
