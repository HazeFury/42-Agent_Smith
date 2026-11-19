"""Extraction of executable Python code from raw LLM output."""

from abc import ABC, abstractmethod
from typing import Any, Literal
from src.core.exceptions import CodeExtractionError
from pydantic import BaseModel, Field
import re
import json


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
    if not name.isidentifier() or not all(k.isidentifier() for k in arguments):
        raise CodeExtractionError(f"Invalid tool name or argument: {name!r}")
    args: str = ""
    args = ", ".join(
        f"{key}={repr(value)}" for key, value in arguments.items())
    return f"result = {name}({args})"


class CodeExtractionResult(BaseModel):
    code: str = Field(..., description="Code to execute")
    thought: str = Field(default="", description="Text before the code")
    source_format: Literal["markdown", "xml", "json", "react"] = Field(
        ..., description="Detected format of the LLM response"
    )
    truncated: bool = Field(
        default=False,
        description="True if the code block had no closing fence",
    )

    def feedback(self) -> str:
        """Build the message telling the LLM how its response was read.

        The subject requires explicit feedback when a code block was
        malformed but interpreted anyway, so the LLM is never left guessing.
        The agent loop should add this message to the observation sent back
        to the LLM.

        Returns:
            An explanation if the code block had no closing fence, or an
            empty string if the response was well-formed.
        """
        if not self.truncated:
            return ""
        return (
            "Warning: your code block had no closing ``` fence. It was "
            "interpreted anyway, from the opening fence up to <end_code> "
            "or the end of your response. Always close your code block "
            "with ``` before <end_code>."
        )


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
    _OPENING = re.compile(r"```(?:python)?[ \t]*\n", re.IGNORECASE)
    _END_CODE = "<end_code>"

    def extract(self, text: str) -> CodeExtractionResult | None:
        text = text.replace("\r\n", "\n")

        blocks = list(self._BLOCK.finditer(text))
        # Skip blocks of other languages (bash, json, ...).
        python_blocks = [
            b for b in blocks
            if b.group(1).strip().lower() in ("", "python")]

        if python_blocks:
            result = python_blocks[0]
            code = result.group(2)
            truncated = False
        else:
            # No closed python block: look for an unclosed opening fence,
            # after the blocks already read (their closing fences excluded).
            last_block_end = blocks[-1].end() if blocks else 0
            new_block_opening = self._OPENING.search(text, last_block_end)
            if not new_block_opening:
                return None
            result = new_block_opening
            # The model may have written <end_code> without closing the fence.
            code = text[new_block_opening.end():].split(self._END_CODE)[0]
            truncated = True

        thought = text[:result.start()].strip()

        code_result = CodeExtractionResult(
            code=code,
            thought=thought,
            source_format="markdown",
            truncated=truncated,
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
        raw_thought = text[:match.start()]
        thought = raw_thought.split("<function_calls>")[0].strip()

        code_extracted = CodeExtractionResult(
            code=code,
            thought=thought,
            source_format="xml",
        )

        return code_extracted


class JSONExtractor(BaseExtractor):
    """Hermes tool calls:
    <tool_call>{"name": "...", "arguments": {...}}</tool_call>.

    Converted to a Python call, e.g. result = read_file(filepath="...").
    """

    _TOOL_CALL = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)

    def extract(self, text: str) -> CodeExtractionResult | None:
        match = self._TOOL_CALL.search(text)

        if not match:
            return None

        json_call_tool = match.group(1)
        try:
            call_tool_dict = json.loads(json_call_tool)
        except json.JSONDecodeError as e:
            raise CodeExtractionError(
                f"Invalid json in <tool_call>: {e}") from e

        if not isinstance(call_tool_dict, dict):
            raise CodeExtractionError("<tool_call> is not a dictionary")

        if "name" not in call_tool_dict:
            raise CodeExtractionError("No key 'name' in json call tool")

        name = call_tool_dict["name"]
        if not isinstance(name, str):
            raise CodeExtractionError(
                "The key 'name' in <tool_call> is not a string")

        arguments = call_tool_dict.get("arguments", {})
        if not isinstance(arguments, dict):
            raise CodeExtractionError("Arguments are not a dictionnary")

        code = build_tool_call(name, arguments)
        thought = text[:match.start()].strip()

        code_extracted = CodeExtractionResult(
            code=code,
            thought=thought,
            source_format="json",
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
                raise CodeExtractionError(
                    f"Invalid json in 'Action Input': {e}") from e
            if not isinstance(data, dict):
                raise CodeExtractionError(
                    "Value of 'Action Input' is not a dictionary")
            arguments = data

        code = build_tool_call(name, arguments)
        thought = text[:match.start()].strip().removeprefix("Thought:").strip()

        code_extracted = CodeExtractionResult(
            code=code,
            thought=thought,
            source_format="react",
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
        # This message is sent back to the LLM as an observation: it must
        # tell the model how to fix its next answer.
        raise CodeExtractionError(
            "No executable code found in your response. Write your "
            "reasoning, then exactly one Python code block:\n"
            "```python\n# your code\n```\n"
            f"Start of your response: {text[:200]!r}")
