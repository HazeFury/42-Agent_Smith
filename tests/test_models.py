"""Tests for data models in src.models.

Validates Pydantic schemas, helper methods, serialization, and security
authorization rules matching the moulinette and architectural specifications.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.models import (
    MBPPTaskInput,
    SandboxConfig,
    SolutionOutput,
    StepMetrics,
    SWEBenchTaskInput,
)


class TestSandboxConfigImportAuthorization:
    """Test suite for SandboxConfig.is_import_authorized."""

    def test_empty_allowlist_rejects_all(self) -> None:
        """Ensure an empty allowlist denies any import attempt."""
        config = SandboxConfig()
        assert not config.is_import_authorized("math")
        assert not config.is_import_authorized("os")
        assert not config.is_import_authorized("sys")

    def test_exact_module_match(self) -> None:
        """Ensure exact matches are accepted and non-matches rejected."""
        config = SandboxConfig(authorized_imports=["math", "json"])
        assert config.is_import_authorized("math")
        assert config.is_import_authorized("json")
        assert not config.is_import_authorized("cmath")
        assert not config.is_import_authorized("os")

    def test_wildcard_authorizes_submodules_and_base(self) -> None:
        """Ensure pattern.* authorizes both submodules and the base package."""
        config = SandboxConfig(authorized_imports=["collections.*"])
        assert config.is_import_authorized("collections")
        assert config.is_import_authorized("collections.abc")
        assert config.is_import_authorized("collections.abc.Mapping")
        assert not config.is_import_authorized("os")

    def test_wildcard_does_not_match_module_prefix_collision(self) -> None:
        """Ensure collections.* does not match collections_extended."""
        config = SandboxConfig(authorized_imports=["collections.*"])
        assert not config.is_import_authorized("collections_extended")
        assert not config.is_import_authorized("collections_utils")

    def test_mixed_rules_allowlist(self) -> None:
        """Ensure mixed exact and wildcard rules work simultaneously."""
        config = SandboxConfig(
            authorized_imports=["math", "collections.*", "typing"]
        )
        assert config.is_import_authorized("math")
        assert config.is_import_authorized("collections")
        assert config.is_import_authorized("collections.defaultdict")
        assert config.is_import_authorized("typing")
        assert not config.is_import_authorized("subprocess")


class TestStepMetrics:
    """Test suite for StepMetrics Pydantic model."""

    def test_step_metrics_creation_and_defaults(self) -> None:
        """Validate creation with required fields and check default values."""
        step = StepMetrics(
            step=1,
            input_tokens=150,
            output_tokens=42,
            request_time_ms=350.5,
        )
        assert step.step == 1
        assert step.input_tokens == 150
        assert step.output_tokens == 42
        assert step.request_time_ms == 350.5
        assert step.retries == 0
        assert step.api_url == ""
        assert step.model_name == ""
        assert step.llm_output == ""
        assert step.sandbox_input == ""
        assert step.sandbox_output == ""
        assert isinstance(step.timestamp, str)


class TestSolutionOutput:
    """Test suite for SolutionOutput Pydantic model and to_file method."""

    @pytest.fixture
    def sample_solution(self) -> SolutionOutput:
        """Return a valid SolutionOutput instance for tests."""
        step = StepMetrics(
            step=1,
            input_tokens=200,
            output_tokens=50,
            request_time_ms=450.0,
            api_url="https://api.openai.com/v1",
            model_name="test-model",
            llm_output="```python\ndef solve(): pass\n```",
            sandbox_input="def solve(): pass",
            sandbox_output="OK",
        )
        return SolutionOutput(
            task_id="mbpp/1",
            benchmark="mbpp",
            success=True,
            solution="def solve(): pass",
            iterations=1,
            total_requests=1,
            total_input_tokens=200,
            total_output_tokens=50,
            total_time_seconds=1.25,
            steps=[step],
            system_prompt="System instructions",
        )

    def test_valid_solution_output_serialization(
        self, sample_solution: SolutionOutput
    ) -> None:
        """Validate model dump produces expected dictionary structure."""
        data = sample_solution.model_dump()
        assert data["task_id"] == "mbpp/1"
        assert data["benchmark"] == "mbpp"
        assert data["success"] is True
        assert data["iterations"] == 1
        assert len(data["steps"]) == 1
        assert data["steps"][0]["step"] == 1

    def test_to_file_creates_file_and_parents(
        self, sample_solution: SolutionOutput, tmp_path: Path
    ) -> None:
        """Ensure to_file creates parent directories and valid JSON output."""
        target_path = tmp_path / "nested" / "eval" / "solution.json"
        assert not target_path.exists()

        sample_solution.to_file(target_path)

        assert target_path.exists()
        content = target_path.read_text(encoding="utf-8")
        parsed = json.loads(content)

        assert parsed["task_id"] == "mbpp/1"
        assert parsed["benchmark"] == "mbpp"
        assert parsed["success"] is True
        assert parsed["iterations"] == 1
        assert parsed["steps"][0]["input_tokens"] == 200

    def test_to_file_with_string_path(
        self, sample_solution: SolutionOutput, tmp_path: Path
    ) -> None:
        """Ensure to_file accepts string path and writes identical JSON."""
        target_file = tmp_path / "solution_str.json"
        sample_solution.to_file(str(target_file))

        assert target_file.exists()
        restored = SolutionOutput.model_validate_json(
            target_file.read_text(encoding="utf-8")
        )
        assert restored.task_id == sample_solution.task_id
        assert restored.solution == sample_solution.solution

    def test_to_file_utf8_encoding(
        self, sample_solution: SolutionOutput, tmp_path: Path
    ) -> None:
        """Ensure non-ASCII characters in solution are preserved in UTF-8."""
        sample_solution.solution = "# Évaluation avec caractères accentués €"
        target_file = tmp_path / "utf8_test.json"
        sample_solution.to_file(target_file)

        raw_text = target_file.read_text(encoding="utf-8")
        assert "Évaluation avec caractères accentués €" in raw_text

    def test_missing_required_field_raises_validation_error(self) -> None:
        """Ensure missing required fields raise Pydantic ValidationError."""
        with pytest.raises(ValidationError):
            SolutionOutput.model_validate({
                "task_id": "1",
                # benchmark missing
                "success": True,
                "solution": "pass",
                "iterations": 1,
                "total_requests": 1,
                "total_input_tokens": 10,
                "total_output_tokens": 10,
                "total_time_seconds": 1.0,
            })


class TestMBPPTaskInput:
    """Test suite for MBPPTaskInput parsing and validation."""

    def test_model_validate_from_dict(self) -> None:
        """Ensure MBPP task dict from moulinette dump is parsed correctly."""
        raw_task = {
            "task_id": 42,
            "task_definition": "Write a function to find min element.",
            "function_definition": "def find_min(lst):",
            "test_imports": ["import math"],
            "test_list": ["assert find_min([1, 2, 3]) == 1"],
        }
        task = MBPPTaskInput.model_validate(raw_task)
        assert task.task_id == 42
        assert task.task_definition == "Write a function to find min element."
        assert task.function_definition == "def find_min(lst):"
        assert task.test_imports == ["import math"]
        assert task.test_list == ["assert find_min([1, 2, 3]) == 1"]

    def test_model_validate_json(self) -> None:
        """Ensure MBPP task raw JSON string is parsed correctly."""
        raw_json = json.dumps({
            "task_id": 10,
            "task_definition": "Return square of number.",
            "function_definition": "def square(n):",
        })
        task = MBPPTaskInput.model_validate_json(raw_json)
        assert task.task_id == 10
        assert task.test_imports == []
        assert task.test_list == []

    def test_missing_required_fields_raises_validation_error(self) -> None:
        """Ensure missing task_definition raises ValidationError."""
        with pytest.raises(ValidationError):
            MBPPTaskInput.model_validate({"task_id": 1})


class TestSWEBenchTaskInput:
    """Test suite for SWEBenchTaskInput parsing and validation."""

    def test_model_validate_from_dict(self) -> None:
        """Ensure SWE-bench task dict is parsed correctly."""
        raw_task = {
            "instance_id": "sympy__sympy-23534",
            "problem_statement": "Fix division by zero in symbols.",
            "docker_image": "swebench/sweb.eval.x86_64.sympy:latest",
            "eval_script": "pytest sympy/core/tests/test_numbers.py",
            "hints_text": "Check denominator check",
            "repo": "sympy/sympy",
        }
        task = SWEBenchTaskInput.model_validate(raw_task)
        assert task.instance_id == "sympy__sympy-23534"
        assert task.docker_image == "swebench/sweb.eval.x86_64.sympy:latest"
        assert task.eval_script == "pytest sympy/core/tests/test_numbers.py"
        assert task.hints_text == "Check denominator check"
        assert task.repo == "sympy/sympy"

    def test_defaults_for_optional_fields(self) -> None:
        """Ensure hints_text and repo have empty string defaults."""
        raw_task = {
            "instance_id": "django__django-12345",
            "problem_statement": "Fix query filter.",
            "docker_image": "swebench/sweb.eval.x86_64.django:latest",
            "eval_script": "./runtests.py",
        }
        task = SWEBenchTaskInput.model_validate(raw_task)
        assert task.hints_text == ""
        assert task.repo == ""

    def test_missing_required_fields_raises_validation_error(self) -> None:
        """Ensure missing docker_image raises ValidationError."""
        with pytest.raises(ValidationError):
            SWEBenchTaskInput.model_validate({
                "instance_id": "test",
                "problem_statement": "issue",
            })
