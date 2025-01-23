import os
from unittest.mock import MagicMock, patch
import pytest
from se_agent.localize.hierarchical import FileLocalizationSuggestion, HierarchicalLocalizationStrategy


@pytest.fixture
def mock_project():
    """Fixture to create a mock project instance."""
    project = MagicMock()
    project.repo_folder = "/mock/repo"
    project.module_src_folder = "/mock/repo/src"
    project_info = MagicMock()
    project_info.src_folder = "src"
    project.project_info = project_info
    return project


@pytest.fixture
def hierarchical_strategy(mock_project):
    """Fixture to create a HierarchicalLocalizationStrategy instance."""
    return HierarchicalLocalizationStrategy(project=mock_project)


@patch("os.path.exists")
def test_file_path_exists(mock_exists, hierarchical_strategy):
    """Test when the file path exists."""
    # Mock the file path to exist
    mock_exists.return_value = True

    suggestion = FileLocalizationSuggestion(
        package="package.subpackage",
        file="file.py",
        confidence=0.9,
        reason="High confidence match"
    )

    # Mock get_file_path to return a valid file path
    hierarchical_strategy.get_file_path = MagicMock(return_value="src/package/subpackage/file.py")

    result = hierarchical_strategy.fuzzy_get_file_path(suggestion)
    assert result == "src/package/subpackage/file.py"
    mock_exists.assert_called_once_with("/mock/repo/src/package/subpackage/file.py")


@patch("os.path.exists")
@patch("os.walk")
def test_fuzzy_correction(mock_walk, mock_exists, hierarchical_strategy):
    """Test when the file path needs fuzzy correction."""
    # Mock the file path to not exist
    mock_exists.return_value = False

    # Simulate os.walk returning a valid path for the file
    mock_walk.return_value = [
        ("/mock/repo/src/package/subpackage", [], ["file.py"]),
    ]

    suggestion = FileLocalizationSuggestion(
        package="file.py",
        file="file.py",
        confidence=0.8,
        reason="Fuzzy match"
    )

    hierarchical_strategy.get_file_path = MagicMock(return_value="src/file/py/file.py")

    result = hierarchical_strategy.fuzzy_get_file_path(suggestion)
    assert result == "src/package/subpackage/file.py"
    mock_walk.assert_called_once_with("/mock/repo/src")
    mock_exists.assert_called_once_with("/mock/repo/src/file/py/file.py")


@patch("os.path.exists")
@patch("os.walk")
def test_no_fuzzy_match(mock_walk, mock_exists, hierarchical_strategy):
    """Test when no fuzzy match can be found."""
    # Mock the file path to not exist
    mock_exists.return_value = False

    # Simulate os.walk not finding the file
    mock_walk.return_value = []

    suggestion = FileLocalizationSuggestion(
        package="package.subpackage",
        file="nonexistent.py",
        confidence=0.5,
        reason="No match"
    )

    hierarchical_strategy.get_file_path = MagicMock(return_value="src/package/subpackage/nonexistent.py")

    result = hierarchical_strategy.fuzzy_get_file_path(suggestion)
    assert result == ""
    mock_walk.assert_called_once_with("/mock/repo/src")
    mock_exists.assert_called_once_with("/mock/repo/src/package/subpackage/nonexistent.py")