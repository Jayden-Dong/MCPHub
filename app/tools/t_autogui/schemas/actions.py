"""Pydantic models for the JSON communication protocol between LLM and executor."""
import json
import re
from typing import Literal, Union, Optional
from pydantic import BaseModel, Field


# --- Action Types ---

class ClickAction(BaseModel):
    """Mouse click action."""
    type: Literal["click"] = "click"
    x: float = Field(ge=0, description="X coordinate (relative 0-1 or absolute pixel value)")
    y: float = Field(ge=0, description="Y coordinate (relative 0-1 or absolute pixel value)")
    button: str = Field(default="left", description="Mouse button: left, right, middle")
    clicks: int = Field(default=1, ge=1, le=3, description="Number of clicks")


class TypeAction(BaseModel):
    """Keyboard text input action."""
    type: Literal["type"] = "type"
    text: str = Field(min_length=1, description="Text to type")


class HotkeyAction(BaseModel):
    """Keyboard shortcut action."""
    type: Literal["hotkey"] = "hotkey"
    keys: list[str] = Field(min_length=1, description="Keys to press, e.g. ['ctrl', 'c'] (use 'ctrl' for Windows, 'command' for macOS)")


class ScrollAction(BaseModel):
    """Mouse scroll action."""
    type: Literal["scroll"] = "scroll"
    x: float = Field(ge=0, description="X coordinate to scroll at (relative 0-1 or absolute pixel value)")
    y: float = Field(ge=0, description="Y coordinate to scroll at (relative 0-1 or absolute pixel value)")
    direction: str = Field(default="down", description="Scroll direction: up or down")
    amount: int = Field(default=3, ge=1, description="Scroll amount")


class DragAction(BaseModel):
    """Mouse drag action for moving files or elements."""
    type: Literal["drag"] = "drag"
    x1: float = Field(ge=0, description="Start X coordinate (relative 0-1 or absolute)")
    y1: float = Field(ge=0, description="Start Y coordinate (relative 0-1 or absolute)")
    x2: float = Field(ge=0, description="End X coordinate (relative 0-1 or absolute)")
    y2: float = Field(ge=0, description="End Y coordinate (relative 0-1 or absolute)")
    button: str = Field(default="left", description="Mouse button: left, right")


class WaitAction(BaseModel):
    """Wait/pause action."""
    type: Literal["wait"] = "wait"
    seconds: float = Field(default=1.0, ge=0.1, le=10.0, description="Seconds to wait")


class FinishedAction(BaseModel):
    """Task completion signal."""
    type: Literal["finished"] = "finished"
    message: str = Field(default="任务完成", description="Completion message")
    user_data: dict = Field(default_factory=dict, description="用户请求的结构化结果数据，以key-value形式保存任务执行中获取到的关键数据")


# --- Discriminated Union ---
ActionType = Union[ClickAction, TypeAction, HotkeyAction, ScrollAction, DragAction, WaitAction, FinishedAction]


# --- LLM Response Model ---

class LLMResponse(BaseModel):
    """Structured response from the LLM containing reasoning and action."""
    thought: str = Field(description="LLM's reasoning about current state and next step")
    action: ActionType = Field(discriminator="type", description="The action to execute")


# --- Step Record ---

class StepRecord(BaseModel):
    """Record of a single execution step for history tracking."""
    step_number: int
    thought: str
    action: ActionType = Field(discriminator="type")
    success: bool = True
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    duration: Optional[float] = Field(default=None, description="Step execution time in seconds, rounded to 2 decimal places")


# --- JSON Parser ---

def parse_llm_response(raw_text: str) -> LLMResponse:
    """Parse LLM output text into a structured LLMResponse.

    Handles multiple formats:
    1. Pure JSON
    2. JSON inside markdown code blocks
    3. JSON embedded in surrounding text

    Args:
        raw_text: Raw text output from LLM

    Returns:
        Parsed and validated LLMResponse

    Raises:
        ValueError: If no valid JSON can be extracted or validation fails
    """
    text = raw_text.strip()

    # Strategy 1: Try direct JSON parse
    try:
        data = json.loads(text)
        return LLMResponse.model_validate(data)
    except (json.JSONDecodeError, Exception):
        pass

    # Strategy 2: Extract from markdown code block
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match.strip())
            return LLMResponse.model_validate(data)
        except (json.JSONDecodeError, Exception):
            continue

    # Strategy 3: Find JSON object in text using brace matching
    brace_depth = 0
    start_idx = None
    for i, char in enumerate(text):
        if char == '{':
            if brace_depth == 0:
                start_idx = i
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
            if brace_depth == 0 and start_idx is not None:
                candidate = text[start_idx:i + 1]
                try:
                    data = json.loads(candidate)
                    return LLMResponse.model_validate(data)
                except (json.JSONDecodeError, Exception):
                    start_idx = None
                    continue

    raise ValueError(
        f"Failed to parse LLM response. Could not extract valid JSON from:\n{text[:500]}"
    )
