"""LLM client for communicating with DashScope API (OpenAI-compatible)."""
import base64
import copy
import io
from typing import Optional

from openai import OpenAI
from PIL import Image

from ..config import setup_logging, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_TOKENS, MAX_IMAGE_HISTORY
from ..schemas import LLMResponse, parse_llm_response
from .prompt import build_system_message

logger = setup_logging("llm")

# Maximum number of retry attempts for parse failures
MAX_PARSE_RETRIES = 3


class LLMClient:
    """Client for multi-turn VLM conversations with DashScope API."""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        self._messages: list[dict] = []
        self._system_message = build_system_message()

    # --- Public API ---

    def reset(self) -> None:
        """Clear conversation history for a new task."""
        self._messages.clear()
        logger.info("Conversation history cleared")

    def chat(
        self,
        screenshot: Image.Image,
        task: str,
        step: int,
        max_steps: int,
        extra_context: str = "",
    ) -> LLMResponse:
        """Send a screenshot + context to the LLM and get a structured response.

        Args:
            screenshot: Current screen capture as PIL Image
            task: The user's task description
            step: Current step number
            max_steps: Maximum allowed steps
            extra_context: Optional additional context (e.g. previous error)

        Returns:
            Parsed and validated LLMResponse

        Raises:
            ValueError: If LLM response cannot be parsed after retries
            Exception: If API call fails
        """
        image_b64 = self._encode_image(screenshot)
        user_message = self._build_user_message(
            image_b64, task, step, max_steps, extra_context
        )
        self._messages.append(user_message)

        # Try to get a valid response with retries on parse failure
        last_error: Optional[str] = None
        for attempt in range(1, MAX_PARSE_RETRIES + 1):
            raw_text = self._call_api()

            try:
                response = parse_llm_response(raw_text)
                # Store assistant reply in history
                self._messages.append({
                    "role": "assistant",
                    "content": raw_text,
                })
                logger.info(
                    "Step %d - thought: %s | action: %s",
                    step, response.thought[:80], response.action.type,
                )
                return response
            except ValueError as e:
                last_error = str(e)
                logger.warning(
                    "Parse attempt %d/%d failed: %s",
                    attempt, MAX_PARSE_RETRIES, last_error[:200],
                )
                if attempt < MAX_PARSE_RETRIES:
                    # Add correction hint and retry
                    self._messages.append({
                        "role": "assistant",
                        "content": raw_text,
                    })
                    self._messages.append({
                        "role": "user",
                        "content": (
                            "你的输出格式不正确，无法解析为有效的 JSON。"
                            "请严格按照要求的 JSON 格式重新输出，"
                            "包含 thought 和 action 字段。"
                        ),
                    })

        raise ValueError(
            f"Failed to get valid response after {MAX_PARSE_RETRIES} attempts. "
            f"Last error: {last_error}"
        )

    @property
    def message_count(self) -> int:
        """Number of messages in the conversation history."""
        return len(self._messages)

    def get_history_summary(self) -> list[dict]:
        """Return a summary of conversation history (roles and text lengths)."""
        summary = []
        for msg in self._messages:
            content = msg["content"]
            if isinstance(content, str):
                length = len(content)
            elif isinstance(content, list):
                length = sum(
                    len(part.get("text", "")) for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            else:
                length = 0
            summary.append({"role": msg["role"], "content_length": length})
        return summary

    # --- Private methods ---

    def _call_api(self) -> str:
        """Make the API call and return the raw response text."""
        messages_to_send = self._trim_images_from_messages(self._messages)
        all_messages = [self._system_message] + messages_to_send
        logger.info(
            "Calling API with %d messages (model=%s, image_limit=%d)",
            len(all_messages), MODEL_NAME, MAX_IMAGE_HISTORY,
        )

        response = self._client.chat.completions.create(
            model=MODEL_NAME,
            messages=all_messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )

        raw_text = response.choices[0].message.content or ""
        logger.debug("API response length: %d chars", len(raw_text))
        return raw_text

    def _trim_images_from_messages(self, messages: list[dict]) -> list[dict]:
        """Trim images from message history based on MAX_IMAGE_HISTORY config.

        Keeps all text content, only removes old images to reduce token usage.
        -1 means keep all images, 0 means no images, N means keep last N images.

        Args:
            messages: Original message list

        Returns:
            New message list with images trimmed (deep copy)
        """
        if MAX_IMAGE_HISTORY < 0:
            # Keep all images
            return messages

        # Deep copy to avoid modifying original messages
        trimmed = copy.deepcopy(messages)

        # Count images from the end (most recent first)
        images_kept = 0
        removed_count = 0

        for msg in reversed(trimmed):
            if msg["role"] != "user":
                continue
            if not isinstance(msg.get("content"), list):
                continue

            # Process each content part in this message
            new_content = []
            for part in msg["content"]:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    # This is an image
                    if MAX_IMAGE_HISTORY == 0:
                        # Remove all images
                        removed_count += 1
                        continue
                    if images_kept < MAX_IMAGE_HISTORY:
                        images_kept += 1
                        new_content.append(part)
                    else:
                        # Remove this old image
                        removed_count += 1
                else:
                    new_content.append(part)

            msg["content"] = new_content

        if removed_count > 0:
            logger.info("Trimmed %d images from history (keeping %d)", removed_count, images_kept)

        return trimmed

    @staticmethod
    def _encode_image(image: Image.Image, quality: int = 85) -> str:
        """Encode a PIL Image to base64 JPEG string.

        Args:
            image: PIL Image to encode
            quality: JPEG quality (1-100), default 85

        Returns:
            Base64-encoded JPEG string
        """
        buffer = io.BytesIO()
        # Convert RGBA to RGB if needed (JPEG doesn't support alpha)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def _build_user_message(
        image_b64: str,
        task: str,
        step: int,
        max_steps: int,
        extra_context: str = "",
    ) -> dict:
        """Build a multimodal user message with screenshot and context.

        Args:
            image_b64: Base64-encoded screenshot
            task: User's task description
            step: Current step number
            max_steps: Maximum steps allowed
            extra_context: Optional additional context

        Returns:
            Message dict in OpenAI multimodal format
        """
        text_parts = [
            f"任务：{task}",
            f"当前是第 {step}/{max_steps} 步。",
        ]
        if extra_context:
            text_parts.append(f"附加信息：{extra_context}")
        text_parts.append("请分析当前屏幕截图并决定下一步操作。")

        return {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "\n".join(text_parts),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}",
                    },
                },
            ],
        }
