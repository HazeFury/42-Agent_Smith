"""Tests for data models in src.models.

Validates Pydantic schemas, helper methods, and security authorization
rules matching the moulinette and architectural specifications.
"""

from src.models import SandboxConfig


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
