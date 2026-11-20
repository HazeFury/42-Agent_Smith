"""Extraction of executable Python code from raw LLM output."""

from abc import ABC, abstractmethod
from typing import Any
from src.core.exceptions import CodeExtractionError
from src.core.logger import get_logger
from src.models.models_private import CodeExtractionResult
import re
import json

logger = get_logger(__name__)

# Error messages are sent back to the LLM as observations. Convention:
# "<what is wrong>. Your <format> was not executed. Expected: <example>."
_JSON_EXAMPLE = (
    '<tool_call>{"name": "read_file", "arguments": {"filepath": "a.py"}}'
    "</tool_call>"
)
_REACT_EXAMPLE = 'Action: read_file\nAction Input: {"filepath": "a.py"}'


def build_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Convert a parsed tool call into a single Python statement.

    Non-Python formats (XML, JSON/Hermes, ReAct) are normalized to Python
    source so that the sandbox stays format-agnostic. For example, the
    ReAct output::

        Action: read_file
        Action Input: {"filepath": "main.py"}

    is parsed by its extractor, then converted by this function:

    >>> build_tool_call("read_file", {"filepath": "main.py"})
    "result = read_file(filepath='main.py')"

    Argument values are rendered with ``repr()``, which yields valid Python
    literals (quotes, escapes, nested structures) with the right types.

    Args:
        name: Tool name, used as the function name in the generated call.
        arguments: Keyword arguments of the call, as decoded from the LLM
            output (JSON-compatible values).

    Returns:
        A single assignment of the form ``result = name(key=value, ...)``.

    Raises:
        CodeExtractionError: If ``name`` or an argument key is not a valid
            Python identifier, which would not produce a single valid call.
    """
    if not name.isidentifier():
        raise CodeExtractionError(
            f"Invalid tool name {name!r}: it must be a valid Python "
            "identifier. Your tool call was not executed.")
    for key in arguments:
        if not key.isidentifier():
            raise CodeExtractionError(
                f"Invalid argument name {key!r} for tool {name!r}: it must "
                "be a valid Python identifier. Your tool call was not "
                "executed.")
    args = ", ".join(
        f"{key}={repr(value)}" for key, value in arguments.items())
    return f"result = {name}({args})"


class BaseExtractor(ABC):
    """Contract shared by all format extractors."""

    @abstractmethod
    def extract(self, text: str) -> CodeExtractionResult | None:
        """Return the extracted code, or None if this format is not found."""


class MarkdownExtractor(BaseExtractor):
    """Python code blocks: ```python ... ``` then optional <end_code>."""

    # Any closed fenced block: group(1) = language tag, group(2) = code.
    # Blocks are read sequentially, so the closing fence of a block is never
    # read as the opening fence of the next one.
    _BLOCK = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)
    # Language tags accepted as Python (an empty tag is a bare fence).
    _PYTHON_TAGS = ("", "python", "py", "python3")
    _OPENING = re.compile(
        r"```(?:" + "|".join(t for t in _PYTHON_TAGS if t) + r")?[ \t]*\n",
        re.IGNORECASE,
    )
    _END_CODE = "<end_code>"

    def extract(self, text: str) -> CodeExtractionResult | None:
        text = text.replace("\r\n", "\n")

        blocks = list(self._BLOCK.finditer(text))
        # Skip blocks of other languages (bash, json, ...).
        python_blocks = [
            b for b in blocks
            if b.group(1).strip().lower() in self._PYTHON_TAGS]

        if python_blocks:
            code = python_blocks[0].group(2)
            truncated = False
            ignored = len(python_blocks) - 1
            # A later unclosed python fence is one more ignored block.
            if self._OPENING.search(text, python_blocks[-1].end()):
                ignored += 1
        else:
            # No closed python block: look for an unclosed opening fence,
            # after the blocks already read (their closing fences excluded).
            last_block_end = blocks[-1].end() if blocks else 0
            new_block_opening = self._OPENING.search(text, last_block_end)
            if not new_block_opening:
                return None
            # The model may have written <end_code> without closing the fence.
            code = text[new_block_opening.end():].split(self._END_CODE)[0]
            truncated = True
            ignored = 0

        code_result = CodeExtractionResult(
            code=code,
            source_format="markdown",
            truncated=truncated,
            ignored_blocks=ignored,
        )

        return code_result


class XMLExtractor(BaseExtractor):
    """
    Anthropic-style tool calls:
    <invoke name="...">
    <parameter name="my_parameter">my_parameter_value</parameter></invoke>.

    Converted to a Python call, e.g. result = read_file(filepath="...").
    """

    _INVOKE = re.compile(r'<invoke name="([^"]+)">(.*?)</invoke>', re.DOTALL)
    _PARAMETER = re.compile(
        r'<parameter name="([^"]+)">(.*?)</parameter>', re.DOTALL)

    def extract(self, text: str) -> CodeExtractionResult | None:
        match = self._INVOKE.search(text)
        if not match:
            return None
        name = match.group(1)
        parameters = dict(self._PARAMETER.findall(match.group(2)))

        code = build_tool_call(name, parameters)

        code_extracted = CodeExtractionResult(
            code=code,
            source_format="xml",
            ignored_blocks=len(self._INVOKE.findall(text)) - 1,
        )

        return code_extracted


class JSONExtractor(BaseExtractor):
    """Hermes tool calls:
    <tool_call>{"name": "...", "arguments": {...}}</tool_call>.

    Converted to a Python call, e.g. result = read_file(filepath="...").
    """

    _TOOL_CALL = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)

    @staticmethod
    def _error(detail: str) -> CodeExtractionError:
        """Build an error following the LLM feedback convention."""
        return CodeExtractionError(
            f"{detail} Your tool call was not executed. "
            f"Expected: {_JSON_EXAMPLE}")

    def extract(self, text: str) -> CodeExtractionResult | None:
        match = self._TOOL_CALL.search(text)

        if not match:
            return None

        json_call_tool = match.group(1)
        try:
            call_tool_dict = json.loads(json_call_tool)
        except json.JSONDecodeError as e:
            raise self._error(
                f"Invalid JSON inside <tool_call>: {e}.") from e

        if not isinstance(call_tool_dict, dict):
            raise self._error(
                "The content of <tool_call> must be a JSON object.")

        if "name" not in call_tool_dict:
            raise self._error("Missing key 'name' in <tool_call>.")

        name = call_tool_dict["name"]
        if not isinstance(name, str):
            raise self._error(
                "Key 'name' in <tool_call> must be a string.")

        arguments = call_tool_dict.get("arguments", {})
        if not isinstance(arguments, dict):
            raise self._error(
                "Key 'arguments' in <tool_call> must be a JSON object.")

        code = build_tool_call(name, arguments)

        code_extracted = CodeExtractionResult(
            code=code,
            source_format="json",
            ignored_blocks=len(self._TOOL_CALL.findall(text)) - 1,
        )

        return code_extracted


class ReActExtractor(BaseExtractor):
    """ReAct format: Action: tool_name / Action Input: {...}.

    (eg:
        Thought: I need to read the file.
        Action: read_file
        Action Input: {"filepath": "main.py"})

    Converted to a Python call, e.g. result = read_file(filepath="...").
    """
    _ACTION = re.compile(r"^Action:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
    _ACTION_INPUT = re.compile(r"^Action Input:[ \t]*", re.MULTILINE)

    @staticmethod
    def _error(detail: str) -> CodeExtractionError:
        """Build an error following the LLM feedback convention."""
        return CodeExtractionError(
            f"{detail} Your action was not executed. "
            f"Expected:\n{_REACT_EXAMPLE}")

    def extract(self, text: str) -> CodeExtractionResult | None:
        match = self._ACTION.search(text)
        if not match:
            return None
        name = match.group(1)

        match_arguments_key = self._ACTION_INPUT.search(text, match.end())
        if not match_arguments_key:
            arguments: dict[str, Any] = {}
        else:
            # raw_decode reads the first complete JSON value and ignores the
            # rest; json.loads would fail on trailing text (Observation: ...).
            try:
                data, _ = json.JSONDecoder().raw_decode(
                    text[match_arguments_key.end():].lstrip())
            except json.JSONDecodeError as e:
                raise self._error(
                    f"Invalid JSON in 'Action Input': {e}.") from e
            if not isinstance(data, dict):
                raise self._error(
                    "'Action Input' must be a JSON object.")
            arguments = data

        code = build_tool_call(name, arguments)

        code_extracted = CodeExtractionResult(
            code=code,
            source_format="react",
            ignored_blocks=len(self._ACTION.findall(text)) - 1,
        )

        return code_extracted


class CodeExtractor:
    """Try each extractor in order.

    raise CodeExtractionError if none matches.
    """

    def __init__(self, extractors: list[BaseExtractor] | None = None) -> None:
        self.extractors: list[BaseExtractor] = (
            extractors
            if extractors is not None
            else [
                MarkdownExtractor(),
                XMLExtractor(),
                JSONExtractor(),
                ReActExtractor(),
            ]
        )

    def extract(self, text: str) -> CodeExtractionResult:
        for extractor in self.extractors:
            result = extractor.extract(text)
            if result is not None:
                return result
        # The excerpt helps debugging but the LLM already knows what it
        # wrote: keep it in the logs, not in the (token-limited) message.
        logger.warning(f"No code found. Response starts with: {text[:200]!r}")
        # This message is sent back to the LLM as an observation: it must
        # tell the model how to fix its next answer.
        raise CodeExtractionError(
            "No executable code found in your response, so nothing was "
            "executed. Write your reasoning, then exactly one Python code "
            "block:\n```python\n# your code\n```")
