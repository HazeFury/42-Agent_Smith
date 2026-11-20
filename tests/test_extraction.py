"""Unit tests for code extraction from raw LLM output."""

from unittest.mock import MagicMock

import pytest

from src.core.exceptions import CodeExtractionError
from src.core.extraction import (
    build_tool_call,
    BaseExtractor,
    CodeExtractionResult,
    CodeExtractor,
    JSONExtractor,
    MarkdownExtractor,
    ReActExtractor,
    XMLExtractor,
)


# --------------------------------------------------------------------------
# MarkdownExtractor
# --------------------------------------------------------------------------


def test_markdown_simple_block() -> None:
    """A closed python block is extracted, not truncated."""
    text = "```python\nprint('hi')\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.code.strip() == "print('hi')"
    assert result.source_format == "markdown"
    assert result.truncated is False


def test_markdown_block_without_language_tag() -> None:
    """The 'python' tag is optional."""
    result = MarkdownExtractor().extract("```\nx = 1\n```")

    assert result is not None
    assert result.code.strip() == "x = 1"


def test_markdown_multiline_code() -> None:
    """Code spanning several lines is kept whole."""
    text = "```python\ndef add(a, b):\n    return a + b\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.code.strip() == "def add(a, b):\n    return a + b"



def test_markdown_truncated_block() -> None:
    """An opening fence with no closing fence yields a non-empty warning."""
    text = "Let me try.\n```python\nx = 1\ny = 2"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.truncated is True
    assert "x = 1" in result.code
    assert "y = 2" in result.code


def test_markdown_end_code_marker_is_removed() -> None:
    """The <end_code> marker after the block never ends up in the code."""
    text = "```python\nprint('hi')\n```<end_code>"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert "<end_code>" not in result.code
    assert result.code.strip() == "print('hi')"


def test_markdown_returns_none_without_block() -> None:
    """Plain text with no fence is not this extractor's format."""
    assert MarkdownExtractor().extract("Just some plain text.") is None


def test_markdown_returns_none_on_empty_text() -> None:
    """An empty response must not crash the extractor."""
    assert MarkdownExtractor().extract("") is None


def test_markdown_takes_first_block_when_several() -> None:
    """Design choice: with several blocks, the first one wins."""
    text = "```python\nfirst = 1\n```\ntext\n```python\nsecond = 2\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.code.strip() == "first = 1"


def test_markdown_end_code_marker_with_space() -> None:
    """A space between the closing fence and <end_code> is tolerated."""
    result = MarkdownExtractor().extract("```python\nx = 1\n``` <end_code>")

    assert result is not None
    assert result.truncated is False
    assert result.code.strip() == "x = 1"


def test_markdown_language_tag_with_trailing_space() -> None:
    """A trailing space after the language tag is tolerated."""
    result = MarkdownExtractor().extract("```python \nx = 1\n```")

    assert result is not None
    assert result.code.strip() == "x = 1"


def test_markdown_language_tag_is_case_insensitive() -> None:
    """'Python' is accepted like 'python'."""
    result = MarkdownExtractor().extract("```Python\nx = 1\n```")

    assert result is not None
    assert result.code.strip() == "x = 1"


def test_markdown_truncated_block_drops_end_code_marker() -> None:
    """<end_code> written without a closing fence must not reach the code."""
    result = MarkdownExtractor().extract("```python\nx = 1\n<end_code>")

    assert result is not None
    assert result.truncated is True
    assert "<end_code>" not in result.code
    assert result.code.strip() == "x = 1"


def test_markdown_empty_block() -> None:
    """An empty closed block gives empty code, not None."""
    result = MarkdownExtractor().extract("```python\n```")

    assert result is not None
    assert result.code == ""
    assert result.truncated is False


def test_markdown_truncated_at_start() -> None:
    """A truncated block at the very start is still extracted."""
    result = MarkdownExtractor().extract("```python\nx = 1")

    assert result is not None
    assert result.truncated is True
    assert result.code == "x = 1"


def test_markdown_keeps_code_indentation() -> None:
    """Indentation inside the block must not be stripped."""
    text = "```python\nif True:\n    x = 1\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert "    x = 1" in result.code


def test_markdown_result_is_valid_python_source() -> None:
    """The extracted code compiles, ready for the sandbox."""
    text = "Plan.\n```python\nfor i in range(3):\n    print(i)\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    compile(result.code, "<llm>", "exec")


def test_markdown_ignores_non_python_block() -> None:
    """A ```bash block is not Python code: this extractor must return None."""
    assert MarkdownExtractor().extract("```bash\nls -la\n```\n") is None


def test_markdown_windows_line_endings() -> None:
    """CRLF line endings must not prevent extraction."""
    result = MarkdownExtractor().extract("```python\r\nx = 1\r\n```")

    assert result is not None
    assert result.code.strip() == "x = 1"


# --------------------------------------------------------------------------
# XMLExtractor
# --------------------------------------------------------------------------


def test_xml_single_parameter() -> None:
    """A simple invoke becomes a Python call."""
    text = (
        '<invoke name="read_file">'
        '<parameter name="filepath">main.py</parameter>'
        "</invoke>"
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"
    assert result.source_format == "xml"
    assert result.truncated is False


def test_xml_several_parameters() -> None:
    """All parameters are passed as keyword arguments."""
    text = (
        '<invoke name="search_code">'
        '<parameter name="pattern">foo</parameter>'
        '<parameter name="path">src</parameter>'
        "</invoke>"
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    assert result.code == "result = search_code(pattern='foo', path='src')"


def test_xml_no_parameter() -> None:
    """An invoke without parameters gives a call without arguments."""
    result = XMLExtractor().extract('<invoke name="list_files"></invoke>')

    assert result is not None
    assert result.code == "result = list_files()"


def test_xml_wrapped_in_function_calls() -> None:
    """The <function_calls> wrapper does not prevent extraction."""
    text = (
        "I will read the file.\n"
        "<function_calls>\n"
        '<invoke name="read_file">\n'
        '<parameter name="filepath">main.py</parameter>\n'
        "</invoke>\n"
        "</function_calls>"
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"


def test_xml_multiline_value_keeps_indentation() -> None:
    """Values are not stripped: edit_file content depends on whitespace."""
    text = (
        '<invoke name="edit_file">'
        '<parameter name="content">def f():\n    return 1\n</parameter>'
        "</invoke>"
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    # Run the generated call against a stub tool that returns its kwargs.
    namespace: dict[str, object] = {"edit_file": lambda **kwargs: kwargs}
    exec(result.code, namespace)
    assert namespace["result"] == {"content": "def f():\n    return 1\n"}


def test_xml_quotes_in_value_stay_valid_python() -> None:
    """repr() keeps quotes inside values from breaking the syntax."""
    text = (
        '<invoke name="run_command">'
        '<parameter name="cmd">echo "it\'s"</parameter>'
        "</invoke>"
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    compile(result.code, "<llm>", "exec")


def test_xml_takes_first_invoke_when_several() -> None:
    """With several calls, the first one wins."""
    text = (
        '<invoke name="first_tool"></invoke>'
        '<invoke name="second_tool"></invoke>'
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    assert result.code == "result = first_tool()"


def test_xml_returns_none_without_invoke() -> None:
    """Plain text is not this extractor's format."""
    assert XMLExtractor().extract("Just some plain text.") is None


def test_xml_returns_none_on_empty_text() -> None:
    """An empty response must not crash the extractor."""
    assert XMLExtractor().extract("") is None


def test_xml_unclosed_invoke_returns_none() -> None:
    """A truncated tool call is never executed."""
    text = '<invoke name="read_file"><parameter name="filepath">x'

    assert XMLExtractor().extract(text) is None


def test_xml_invalid_tool_name_raises() -> None:
    """A tool name that is not an identifier is rejected."""
    text = '<invoke name="x(); import os">' "</invoke>"

    with pytest.raises(CodeExtractionError):
        XMLExtractor().extract(text)


# --------------------------------------------------------------------------
# JSONExtractor
# --------------------------------------------------------------------------


def _tool_call(payload: str) -> str:
    return f"<tool_call>{payload}</tool_call>"


def test_json_simple_call() -> None:
    """A Hermes tool call becomes a Python call."""
    text = _tool_call(
        '{"name": "read_file", "arguments": {"filepath": "main.py"}}')
    result = JSONExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"
    assert result.source_format == "json"
    assert result.truncated is False


def test_json_several_arguments() -> None:
    """All arguments are passed as keyword arguments."""
    text = _tool_call(
        '{"name": "search_code", "arguments": '
        '{"pattern": "foo", "path": "src"}}')
    result = JSONExtractor().extract(text)

    assert result is not None
    assert result.code == "result = search_code(pattern='foo', path='src')"


def test_json_missing_arguments_means_no_argument() -> None:
    """A call without 'arguments' is valid: the tool takes no parameter."""
    result = JSONExtractor().extract(_tool_call('{"name": "list_files"}'))

    assert result is not None
    assert result.code == "result = list_files()"


def test_json_empty_arguments() -> None:
    """An empty 'arguments' object gives a call without arguments."""
    text = _tool_call('{"name": "list_files", "arguments": {}}')
    result = JSONExtractor().extract(text)

    assert result is not None
    assert result.code == "result = list_files()"


def test_json_value_types_are_preserved() -> None:
    """JSON true/null/numbers/lists/objects become the matching Python."""
    text = _tool_call(
        '{"name": "tool", "arguments": {"count": 3, "ratio": 0.5, '
        '"flag": true, "nothing": null, "items": [1, 2], '
        '"nested": {"a": {"b": "c"}}}}')
    result = JSONExtractor().extract(text)

    assert result is not None
    # Run the generated call against a stub tool that returns its kwargs.
    namespace: dict[str, object] = {"tool": lambda **kwargs: kwargs}
    exec(result.code, namespace)
    assert namespace["result"] == {
        "count": 3,
        "ratio": 0.5,
        "flag": True,
        "nothing": None,
        "items": [1, 2],
        "nested": {"a": {"b": "c"}},
    }


def test_json_multiline_payload() -> None:
    """JSON spread over several lines works."""
    text = (
        "I will read the file.\n"
        "<tool_call>\n"
        "{\n"
        '  "name": "read_file",\n'
        '  "arguments": {"filepath": "main.py"}\n'
        "}\n"
        "</tool_call>"
    )
    result = JSONExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"


def test_json_quotes_and_newlines_in_value_stay_valid_python() -> None:
    """repr() keeps special characters from breaking the syntax."""
    text = _tool_call(
        '{"name": "tool", "arguments": {"text": "say \\"hi\\"\\nit\'s"}}')
    result = JSONExtractor().extract(text)

    assert result is not None
    namespace: dict[str, object] = {"tool": lambda **kwargs: kwargs}
    exec(result.code, namespace)
    assert namespace["result"] == {"text": "say \"hi\"\nit's"}


def test_json_takes_first_tool_call_when_several() -> None:
    """With several calls, the first one wins."""
    text = _tool_call('{"name": "first_tool"}') + _tool_call(
        '{"name": "second_tool"}')
    result = JSONExtractor().extract(text)

    assert result is not None
    assert result.code == "result = first_tool()"


def test_json_returns_none_without_tag() -> None:
    """Plain text is not this extractor's format."""
    assert JSONExtractor().extract("Just some plain text.") is None


def test_json_returns_none_on_empty_text() -> None:
    """An empty response must not crash the extractor."""
    assert JSONExtractor().extract("") is None


def test_json_unclosed_tool_call_returns_none() -> None:
    """A truncated tool call is never executed."""
    text = '<tool_call>{"name": "read_file", "arguments": {"filepath": "x'

    assert JSONExtractor().extract(text) is None


def test_json_invalid_json_raises() -> None:
    """Malformed JSON inside the tag gives an explicit error."""
    with pytest.raises(CodeExtractionError, match="Invalid JSON"):
        JSONExtractor().extract(_tool_call('{"name": "read_file", '))


def test_json_missing_name_raises() -> None:
    """A tool call without a name cannot be converted."""
    with pytest.raises(CodeExtractionError, match="name"):
        JSONExtractor().extract(_tool_call('{"arguments": {"a": 1}}'))


def test_json_name_must_be_a_string() -> None:
    """A non-string name raises CodeExtractionError, not AttributeError."""
    with pytest.raises(CodeExtractionError):
        JSONExtractor().extract(_tool_call('{"name": 123}'))


def test_json_payload_must_be_an_object() -> None:
    """A JSON list or scalar is not a tool call."""
    for payload in ('["read_file"]', '"read_file"', "42"):
        with pytest.raises(CodeExtractionError):
            JSONExtractor().extract(_tool_call(payload))


def test_json_arguments_must_be_an_object() -> None:
    """'arguments' given as a list or string is rejected."""
    for arguments in ('["a"]', '"a"', "1"):
        text = _tool_call(f'{{"name": "tool", "arguments": {arguments}}}')
        with pytest.raises(CodeExtractionError):
            JSONExtractor().extract(text)


def test_json_invalid_tool_name_raises() -> None:
    """A tool name that is not an identifier is rejected."""
    with pytest.raises(CodeExtractionError):
        JSONExtractor().extract(_tool_call('{"name": "x(); import os"}'))


# --------------------------------------------------------------------------
# ReActExtractor
# --------------------------------------------------------------------------


def test_react_simple_call() -> None:
    """Action / Action Input become a Python call."""
    text = (
        "Thought: I need to read the file.\n"
        "Action: read_file\n"
        'Action Input: {"filepath": "main.py"}'
    )
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"
    assert result.source_format == "react"
    assert result.truncated is False





def test_react_several_arguments() -> None:
    """All keys of Action Input are passed as keyword arguments."""
    text = (
        "Action: search_code\n"
        'Action Input: {"pattern": "foo", "path": "src"}'
    )
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = search_code(pattern='foo', path='src')"


def test_react_missing_action_input_means_no_argument() -> None:
    """An action without input is a call without arguments."""
    result = ReActExtractor().extract("Action: list_files\n")

    assert result is not None
    assert result.code == "result = list_files()"


def test_react_empty_action_input() -> None:
    """An empty JSON object gives a call without arguments."""
    result = ReActExtractor().extract("Action: list_files\nAction Input: {}")

    assert result is not None
    assert result.code == "result = list_files()"


def test_react_value_types_are_preserved() -> None:
    """JSON true/null/numbers/lists/objects become the matching Python."""
    text = (
        "Action: tool\n"
        'Action Input: {"count": 3, "flag": true, "nothing": null, '
        '"items": [1, 2], "nested": {"a": "b"}}'
    )
    result = ReActExtractor().extract(text)

    assert result is not None
    namespace: dict[str, object] = {"tool": lambda **kwargs: kwargs}
    exec(result.code, namespace)
    assert namespace["result"] == {
        "count": 3,
        "flag": True,
        "nothing": None,
        "items": [1, 2],
        "nested": {"a": "b"},
    }


def test_react_multiline_json_on_next_line() -> None:
    """The JSON may start on the line after 'Action Input:'."""
    text = (
        "Action: read_file\n"
        "Action Input:\n"
        "{\n"
        '  "filepath": "main.py"\n'
        "}"
    )
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"


def test_react_ignores_hallucinated_observation_and_next_step() -> None:
    """Text after the JSON (invented observation, 2nd action) is ignored."""
    text = (
        "Thought: read it.\n"
        "Action: read_file\n"
        'Action Input: {"filepath": "main.py"}\n'
        "Observation: print('hello')\n"
        "Thought: now edit.\n"
        "Action: edit_file\n"
        'Action Input: {"filepath": "main.py"}'
    )
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = read_file(filepath='main.py')"


def test_react_action_input_before_action_is_ignored() -> None:
    """Only an Action Input located after the Action is used."""
    text = 'Action Input: {"a": 1}\nAction: tool\n'
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = tool()"


def test_react_final_answer_is_a_regular_call() -> None:
    """final_answer needs no special case."""
    text = 'Action: final_answer\nAction Input: {"answer": "42"}'
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = final_answer(answer='42')"


def test_react_returns_none_without_action() -> None:
    """Plain text is not this extractor's format."""
    assert ReActExtractor().extract("Just some plain text.") is None


def test_react_returns_none_on_empty_text() -> None:
    """An empty response must not crash the extractor."""
    assert ReActExtractor().extract("") is None


def test_react_action_in_middle_of_sentence_is_ignored() -> None:
    """'Action:' must start a line to count."""
    assert ReActExtractor().extract("The next Action: read_file.") is None


def test_react_truncated_json_raises() -> None:
    """A cut-off Action Input is never executed."""
    text = 'Action: read_file\nAction Input: {"filepath": "ma'

    with pytest.raises(CodeExtractionError):
        ReActExtractor().extract(text)


def test_react_action_input_not_json_raises() -> None:
    """A plain string after Action Input is rejected explicitly."""
    with pytest.raises(CodeExtractionError):
        ReActExtractor().extract("Action: read_file\nAction Input: main.py")


def test_react_action_input_must_be_an_object() -> None:
    """A JSON list or scalar is not a set of keyword arguments."""
    for payload in ('["a"]', '"a"', "42"):
        text = f"Action: tool\nAction Input: {payload}"
        with pytest.raises(CodeExtractionError):
            ReActExtractor().extract(text)


def test_react_invalid_tool_name_raises() -> None:
    """A tool name that is not an identifier is rejected."""
    with pytest.raises(CodeExtractionError):
        ReActExtractor().extract("Action: x(); import os\n")


# --------------------------------------------------------------------------
# CodeExtractor (dispatcher)
# --------------------------------------------------------------------------


class _StubExtractor(BaseExtractor):
    """Test double: returns a fixed result and records the text received."""

    def __init__(self, result: CodeExtractionResult | None) -> None:
        self.result = result
        self.received: list[str] = []

    def extract(self, text: str) -> CodeExtractionResult | None:
        self.received.append(text)
        return self.result


def _result(code: str, fmt: str = "markdown") -> CodeExtractionResult:
    return CodeExtractionResult(code=code, source_format=fmt)  # type: ignore


def test_dispatcher_returns_first_non_none_result() -> None:
    """Extractors are tried in order; the first match wins."""
    first = _StubExtractor(None)
    second = _StubExtractor(_result("from_second", "json"))
    third = _StubExtractor(_result("from_third", "react"))

    result = CodeExtractor([first, second, third]).extract("anything")

    assert result.code == "from_second"
    assert third.received == []  # never reached


def test_dispatcher_passes_text_to_extractors() -> None:
    """Each extractor must receive the raw LLM text."""
    stub = _StubExtractor(_result("x"))
    CodeExtractor([stub]).extract("raw llm text")

    assert stub.received == ["raw llm text"]


def test_dispatcher_raises_when_nothing_matches() -> None:
    """If every extractor returns None, CodeExtractionError is raised."""
    extractor = CodeExtractor([_StubExtractor(None), _StubExtractor(None)])

    with pytest.raises(CodeExtractionError):
        extractor.extract("no code here")


def test_dispatcher_error_message_does_not_echo_response() -> None:
    """The LLM knows what it wrote: echoing it would waste input tokens."""
    extractor = CodeExtractor([_StubExtractor(None)])

    with pytest.raises(CodeExtractionError) as exc_info:
        extractor.extract("hello world")

    assert "hello world" not in exc_info.value.message


def test_dispatcher_logs_response_excerpt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The start of the response goes to the logs for debugging."""
    fake_logger = MagicMock()
    monkeypatch.setattr("src.core.extraction.logger", fake_logger)
    extractor = CodeExtractor([_StubExtractor(None)])

    with pytest.raises(CodeExtractionError):
        extractor.extract("hello world")

    assert "hello world" in fake_logger.warning.call_args.args[0]


def test_dispatcher_error_message_says_nothing_was_executed() -> None:
    """The LLM is told explicitly that nothing ran."""
    extractor = CodeExtractor([_StubExtractor(None)])

    with pytest.raises(CodeExtractionError, match="nothing was executed"):
        extractor.extract("no code here")


def test_dispatcher_error_message_explains_expected_format() -> None:
    """The error is feedback for the LLM: it states the format to use."""
    extractor = CodeExtractor([_StubExtractor(None)])

    with pytest.raises(CodeExtractionError, match="```python"):
        extractor.extract("no code here")


def test_dispatcher_error_message_has_constant_size() -> None:
    """The message size does not depend on the length of the response."""
    extractor = CodeExtractor([_StubExtractor(None)])
    messages = []
    for text in ("a", "b" * 5000):
        with pytest.raises(CodeExtractionError) as exc_info:
            extractor.extract(text)
        messages.append(exc_info.value.message)

    assert messages[0] == messages[1]


def test_dispatcher_empty_list_is_respected() -> None:
    """An explicit empty list must not fall back to the default extractors."""
    with pytest.raises(CodeExtractionError):
        CodeExtractor([]).extract("```python\nx = 1\n```")


def test_dispatcher_default_handles_markdown() -> None:
    """With defaults, a markdown block is extracted end to end."""
    result = CodeExtractor().extract("Plan.\n```python\nx = 1\n```")

    assert result.source_format == "markdown"
    assert result.code.strip() == "x = 1"



def test_feedback_empty_for_closed_block() -> None:
    """A well-formed block produces no feedback."""
    result = CodeExtractor().extract("```python\nprint(1)\n```")
    assert result.feedback() == ""


def test_feedback_explains_unclosed_block() -> None:
    """An unclosed block gets an explanation for the LLM."""
    result = CodeExtractor().extract("```python\nprint(1)\n<end_code>")
    message = result.feedback()
    assert "no closing" in message
    assert "<end_code>" in message


@pytest.mark.parametrize("tag", ["py", "python3", "Python", "PY"])
def test_markdown_python_tag_variants_closed(tag: str) -> None:
    """py / python3 (any case) are accepted as Python blocks."""
    result = MarkdownExtractor().extract(f"```{tag}\nx = 1\n```")

    assert result is not None
    assert result.code.strip() == "x = 1"
    assert result.truncated is False


@pytest.mark.parametrize("tag", ["py", "python3"])
def test_markdown_python_tag_variants_unclosed(tag: str) -> None:
    """An unclosed py / python3 block is recovered and flagged."""
    result = MarkdownExtractor().extract(f"```{tag}\nx = 1")

    assert result is not None
    assert result.code == "x = 1"
    assert result.truncated is True


@pytest.mark.parametrize("tag", ["bash", "json", "pycon", "python2"])
def test_markdown_other_language_tags_still_ignored(tag: str) -> None:
    """Non-Python tags (even similar ones) are not executed."""
    assert MarkdownExtractor().extract(f"```{tag}\nx = 1\n```") is None
    assert MarkdownExtractor().extract(f"```{tag}\nx = 1") is None


# --------------------------------------------------------------------------
# Ignored blocks / tool calls
# --------------------------------------------------------------------------


def test_markdown_two_blocks_first_used_second_ignored() -> None:
    """Only the first python block is executed; the other is counted."""
    text = "```python\nx = 1\n```\nthen\n```python\ny = 2\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.code.strip() == "x = 1"
    assert result.ignored_blocks == 1


def test_markdown_three_blocks_counts_two_ignored() -> None:
    """Every extra python block is counted."""
    block = "```python\nx = 1\n```\n"
    result = MarkdownExtractor().extract(block * 3)

    assert result is not None
    assert result.ignored_blocks == 2


def test_markdown_single_block_ignores_nothing() -> None:
    """One block means nothing ignored and no feedback."""
    result = CodeExtractor().extract("```python\nx = 1\n```")

    assert result.ignored_blocks == 0
    assert result.feedback() == ""


def test_markdown_other_language_blocks_not_counted() -> None:
    """A bash block between python blocks is not a python block."""
    text = "```python\nx = 1\n```\n```bash\nls\n```"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.ignored_blocks == 0


def test_markdown_later_unclosed_block_counted() -> None:
    """A closed block followed by an unclosed one: the latter is ignored."""
    text = "```python\nx = 1\n```\n```python\ny = 2"
    result = MarkdownExtractor().extract(text)

    assert result is not None
    assert result.code.strip() == "x = 1"
    assert result.ignored_blocks == 1


def test_xml_two_invokes_second_ignored() -> None:
    """Only the first <invoke> is converted; the other is counted."""
    text = (
        '<invoke name="a"></invoke>\n'
        '<invoke name="b"></invoke>'
    )
    result = XMLExtractor().extract(text)

    assert result is not None
    assert result.code == "result = a()"
    assert result.ignored_blocks == 1


def test_json_two_tool_calls_second_ignored() -> None:
    """Only the first <tool_call> is converted; the other is counted."""
    text = (
        '<tool_call>{"name": "a"}</tool_call>\n'
        '<tool_call>{"name": "b"}</tool_call>'
    )
    result = JSONExtractor().extract(text)

    assert result is not None
    assert result.code == "result = a()"
    assert result.ignored_blocks == 1


def test_react_two_actions_second_ignored() -> None:
    """Only the first Action is converted; the other is counted."""
    text = "Action: a\nObservation: fake\nAction: b\n"
    result = ReActExtractor().extract(text)

    assert result is not None
    assert result.code == "result = a()"
    assert result.ignored_blocks == 1


@pytest.mark.parametrize("extractor,text", [
    (XMLExtractor(), '<invoke name="a"></invoke>'),
    (JSONExtractor(), '<tool_call>{"name": "a"}</tool_call>'),
    (ReActExtractor(), "Action: a"),
])
def test_single_tool_call_ignores_nothing(
    extractor: BaseExtractor, text: str
) -> None:
    """One tool call means nothing ignored and no feedback."""
    result = extractor.extract(text)

    assert result is not None
    assert result.ignored_blocks == 0
    assert result.feedback() == ""


def test_feedback_mentions_ignored_code_blocks() -> None:
    """Markdown feedback speaks of code blocks and asks for exactly one."""
    result = CodeExtractor().extract(
        "```python\nx = 1\n```\n```python\ny = 2\n```")
    message = result.feedback()

    assert "first code block" in message
    assert "1 other code block(s)" in message
    assert "exactly one code block" in message


def test_feedback_mentions_ignored_tool_calls() -> None:
    """Tool-call formats speak of tool calls, not code blocks."""
    result = CodeExtractor().extract("Action: a\nAction: b\n")
    message = result.feedback()

    assert "first tool call" in message
    assert "code block" not in message


def test_feedback_combines_truncated_and_ignored() -> None:
    """Both issues are reported, one line each."""
    result = CodeExtractionResult(
        code="x = 1", source_format="markdown",
        truncated=True, ignored_blocks=2)
    lines = result.feedback().splitlines()

    assert len(lines) == 2
    assert "no closing" in lines[0]
    assert "2 other code block(s)" in lines[1]


# --------------------------------------------------------------------------
# Error messages (feedback for the LLM)
# --------------------------------------------------------------------------


def test_invalid_tool_name_message_names_the_tool() -> None:
    """A bad tool name is reported as such, with the rule to follow."""
    with pytest.raises(CodeExtractionError) as exc_info:
        build_tool_call("read-file", {})

    message = exc_info.value.message
    assert "Invalid tool name 'read-file'" in message
    assert "valid Python identifier" in message
    assert "not executed" in message


def test_invalid_argument_name_message_names_the_argument() -> None:
    """A bad argument is not blamed on the (valid) tool name."""
    with pytest.raises(CodeExtractionError) as exc_info:
        build_tool_call("read_file", {"file-path": "a.py"})

    message = exc_info.value.message
    assert "Invalid argument name 'file-path'" in message
    assert "tool 'read_file'" in message
    assert "Invalid tool name" not in message


@pytest.mark.parametrize("text", [
    _tool_call('{"name": "read_file", '),
    _tool_call('["read_file"]'),
    _tool_call('{"arguments": {"a": 1}}'),
    _tool_call('{"name": 123}'),
    _tool_call('{"name": "t", "arguments": ["a"]}'),
])
def test_json_errors_follow_the_convention(text: str) -> None:
    """Every JSON error says the call was not run and shows the format."""
    with pytest.raises(CodeExtractionError) as exc_info:
        JSONExtractor().extract(text)

    message = exc_info.value.message
    assert "Your tool call was not executed." in message
    assert '<tool_call>{"name": "read_file"' in message


@pytest.mark.parametrize("text", [
    'Action: read_file\nAction Input: {"filepath": "ma',
    "Action: read_file\nAction Input: main.py",
    "Action: tool\nAction Input: [1]",
])
def test_react_errors_follow_the_convention(text: str) -> None:
    """Every ReAct error says the action was not run and shows the format."""
    with pytest.raises(CodeExtractionError) as exc_info:
        ReActExtractor().extract(text)

    message = exc_info.value.message
    assert "Your action was not executed." in message
    assert "Action Input:" in message
