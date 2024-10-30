import json
import os
import pytest
from unittest.mock import patch, MagicMock
from se_agent.project import Project
from se_agent.project_info import ProjectInfo

@pytest.fixture
def project_fixture(tmp_path):
    # Set up a temporary directory for testing
    projects_store = tmp_path / "projects_store"
    os.makedirs(projects_store, exist_ok=True)

    # Mock project information
    project_info = ProjectInfo(
        repo_full_name="test_owner/test_repo",
        github_token="fake_token",
        api_url=None,
        src_folder="src"
    )

    # Create a Project instance
    project = Project(
        github_token="fake_token",
        projects_store=str(projects_store),
        project_info=project_info
    )

    # Create mock repository structure (reflects your change of subpackage under package2)
    src_folder = os.path.join(project.module_src_folder)
    os.makedirs(src_folder, exist_ok=True)

    # Create some mock Python files in the repository
    files = {
        "package1/module1.py": "# This is module1.py\nprint('Hello from module1.py')",
        "package2/module2.py": "# This is module2.py\nprint('Hello from module2.py')",
        "package2/subpackage/module3.py": "# This is module3.py in subpackage\nprint('Hello from module3.py')",
    }

    for file, content in files.items():
        file_path = os.path.join(src_folder, file)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)

    return project

@patch("se_agent.project.generate_semantic_description", return_value="Mock summary")
@patch("se_agent.project.generate_package_summary", return_value="Mock package summary")
@patch.object(Project, "fetch_package_details", return_value="Mock package details")
@patch.object(Project, "pull_latest_changes")
def test_update_codebase_understanding(
    mock_pull_latest,
    mock_fetch_package_details,
    mock_generate_package_summary,
    mock_generate_semantic_description,
    project_fixture
):
    project = project_fixture

    # Call the method with no modified_files to force a full update
    project.update_codebase_understanding()

    # Check that pull_latest_changes was called
    mock_pull_latest.assert_called_once()

    # Check that generate_semantic_description was called for each Python file
    expected_files = [
        os.path.join(project.module_src_folder, "package1/module1.py"),
        os.path.join(project.module_src_folder, "package2/module2.py"),
        os.path.join(project.module_src_folder, "package2/subpackage/module3.py")
    ]
    assert mock_generate_semantic_description.call_count == 3
    for expected_file in expected_files:
        mock_generate_semantic_description.assert_any_call(expected_file)

    # Check that fetch_package_details was called for each top-level package separately
    assert mock_fetch_package_details.call_count == 2
    mock_fetch_package_details.assert_any_call(["package1"])
    mock_fetch_package_details.assert_any_call(["package2"])

    # Check that generate_package_summary was called for the top-level packages
    assert mock_generate_package_summary.call_count == 2
    mock_generate_package_summary.assert_any_call("package1", "Mock package details")
    mock_generate_package_summary.assert_any_call("package2", "Mock package details")

    # Verify that the generated summaries are written to the correct locations
    expected_summaries = {
        "package1/module1.py.md": "Mock summary",
        "package2/module2.py.md": "Mock summary",
        "package2/subpackage/module3.py.md": "Mock summary"
    }

    for relative_path, expected_content in expected_summaries.items():
        summary_path = os.path.join(project.package_details_folder, relative_path)
        assert os.path.exists(summary_path)
        with open(summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the package summaries are written to the correct locations
    expected_package_summaries = {
        "package1.md": "Mock package summary",
        "package2.md": "Mock package summary"
    }

    for relative_path, expected_content in expected_package_summaries.items():
        package_summary_path = os.path.join(project.package_summaries_folder, relative_path)
        assert os.path.exists(package_summary_path)
        with open(package_summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the checkpoint file is deleted after successful processing
    assert not os.path.exists(project.checkpoint_file)

@patch("se_agent.project.generate_semantic_description", return_value="Mock summary")
@patch("se_agent.project.generate_package_summary", return_value="Mock package summary")
@patch.object(Project, "fetch_package_details", return_value="Mock package details")
@patch.object(Project, "pull_latest_changes")
def test_update_codebase_understanding_with_checkpoint(
    mock_pull_latest,
    mock_fetch_package_details,
    mock_generate_package_summary,
    mock_generate_semantic_description,
    project_fixture
):
    project = project_fixture

    # Ensure metadata folder exists for checkpoint saving
    os.makedirs(project.metadata_folder, exist_ok=True)

    # Simulate an interruption after processing the first file
    project.checkpoint_data['files_processed'] = ["package1/module1.py"]
    project.checkpoint_data['packages_processed'] = ["package1"]
    project.checkpoint_data['unprocessed'] = {"package2": ["package2/module2.py", "package2/subpackage/module3.py"]}
    project.save_checkpoint()

    # Ensure package details and summaries folders exist for writing summaries
    os.makedirs(project.package_details_folder, exist_ok=True)
    os.makedirs(project.package_summaries_folder, exist_ok=True)

    # Create summaries for already processed files and packages
    os.makedirs(os.path.dirname(os.path.join(project.package_details_folder, "package1/module1.py.md")), exist_ok=True)
    with open(os.path.join(project.package_details_folder, "package1/module1.py.md"), "w") as f:
        f.write("Mock summary")
    with open(os.path.join(project.package_summaries_folder, "package1.md"), "w") as f:
        f.write("Mock package summary")

    # Call the method again to resume from the checkpoint
    project.update_codebase_understanding()

    # Check that pull_latest_changes was called
    mock_pull_latest.assert_called_once()

    # Check that generate_semantic_description was called for the remaining Python files
    expected_remaining_files = [
        os.path.join(project.module_src_folder, "package2/module2.py"),
        os.path.join(project.module_src_folder, "package2/subpackage/module3.py")
    ]
    assert mock_generate_semantic_description.call_count == 2
    for expected_file in expected_remaining_files:
        mock_generate_semantic_description.assert_any_call(expected_file)

    # Check that fetch_package_details was called for each top-level package separately
    assert mock_fetch_package_details.call_count == 1
    mock_fetch_package_details.assert_any_call(["package2"])

    # Check that generate_package_summary was called for the top-level package
    assert mock_generate_package_summary.call_count == 1
    mock_generate_package_summary.assert_any_call("package2", "Mock package details")

    # Verify that the generated summaries are written to the correct locations
    expected_summaries = {
        "package1/module1.py.md": "Mock summary",
        "package2/module2.py.md": "Mock summary",
        "package2/subpackage/module3.py.md": "Mock summary"
    }

    for relative_path, expected_content in expected_summaries.items():
        summary_path = os.path.join(project.package_details_folder, relative_path)
        assert os.path.exists(summary_path)
        with open(summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the package summaries are written to the correct locations
    expected_package_summaries = {
        "package1.md": "Mock package summary",
        "package2.md": "Mock package summary"
    }

    for relative_path, expected_content in expected_package_summaries.items():
        package_summary_path = os.path.join(project.package_summaries_folder, relative_path)
        assert os.path.exists(package_summary_path)
        with open(package_summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the checkpoint file is deleted after successful processing
    assert not os.path.exists(project.checkpoint_file)

@patch("se_agent.project.generate_semantic_description", return_value="Mock summary")
@patch("se_agent.project.generate_package_summary", side_effect=Exception("Mock package summary error"))
@patch.object(Project, "fetch_package_details", return_value="Mock package details")
@patch.object(Project, "pull_latest_changes")
def test_update_codebase_understanding_package_summary_error(
    mock_pull_latest,
    mock_fetch_package_details,
    mock_generate_package_summary,
    mock_generate_semantic_description,
    project_fixture
):
    project = project_fixture

    # Call the method to simulate an error during package summary generation
    project.update_codebase_understanding()

    # Check that pull_latest_changes was called
    mock_pull_latest.assert_called_once()

    # Check that generate_semantic_description was called for each Python file
    expected_files = [
        os.path.join(project.module_src_folder, "package1/module1.py"),
        os.path.join(project.module_src_folder, "package2/module2.py"),
        os.path.join(project.module_src_folder, "package2/subpackage/module3.py")
    ]
    assert mock_generate_semantic_description.call_count == 3
    for expected_file in expected_files:
        mock_generate_semantic_description.assert_any_call(expected_file)

    # Check that fetch_package_details was called for each top-level package separately
    assert mock_fetch_package_details.call_count == 2
    mock_fetch_package_details.assert_any_call(["package1"])
    mock_fetch_package_details.assert_any_call(["package2"])

    # Check that generate_package_summary was called and failed for the top-level packages
    assert mock_generate_package_summary.call_count == 2
    mock_generate_package_summary.assert_any_call("package1", "Mock package details")
    mock_generate_package_summary.assert_any_call("package2", "Mock package details")

    # Verify that the checkpoint file still exists after the error
    assert os.path.exists(project.checkpoint_file)

    # Load the checkpoint data and verify that all files are marked as processed
    with open(project.checkpoint_file, "r") as f:
        checkpoint_data = json.load(f)
    assert set(checkpoint_data['files_processed']) == set(["package1/module1.py", "package2/module2.py", "package2/subpackage/module3.py"])
    assert "package1" not in checkpoint_data['packages_processed']
    assert "package2" not in checkpoint_data['packages_processed']

@patch("se_agent.project.generate_semantic_description", return_value="Mock summary")
@patch("se_agent.project.generate_package_summary", return_value="Mock package summary")
@patch.object(Project, "fetch_package_details", return_value="Mock package details")
@patch.object(Project, "pull_latest_changes")
def test_update_codebase_understanding_resume_from_checkpoint(
    mock_pull_latest,
    mock_fetch_package_details,
    mock_generate_package_summary,
    mock_generate_semantic_description,
    project_fixture
):
    project = project_fixture

    # Ensure metadata folder exists for checkpoint saving
    os.makedirs(project.metadata_folder, exist_ok=True)

    # Simulate a checkpoint with some files already processed
    project.checkpoint_data['files_processed'] = ["package1/module1.py", "package2/module2.py"]
    project.checkpoint_data['packages_processed'] = ["package1"]
    project.checkpoint_data['unprocessed'] = {"package2": ["package2/subpackage/module3.py"]}
    project.save_checkpoint()

    # Ensure package details and summaries folders exist for writing summaries
    os.makedirs(project.package_details_folder, exist_ok=True)
    os.makedirs(project.package_summaries_folder, exist_ok=True)

    # Create summaries for already processed files and packages
    os.makedirs(os.path.dirname(os.path.join(project.package_details_folder, "package1/module1.py.md")), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.join(project.package_details_folder, "package2/module2.py.md")), exist_ok=True)
    with open(os.path.join(project.package_details_folder, "package1/module1.py.md"), "w") as f:
        f.write("Mock summary")
    with open(os.path.join(project.package_details_folder, "package2/module2.py.md"), "w") as f:
        f.write("Mock summary")
    with open(os.path.join(project.package_summaries_folder, "package1.md"), "w") as f:
        f.write("Mock package summary")

    # Call the method again to resume from the checkpoint
    project.update_codebase_understanding()

    # Check that pull_latest_changes was called
    mock_pull_latest.assert_called_once()

    # Check that generate_semantic_description was called only for the remaining Python file
    expected_remaining_file = os.path.join(project.module_src_folder, "package2/subpackage/module3.py")
    assert mock_generate_semantic_description.call_count == 1
    mock_generate_semantic_description.assert_any_call(expected_remaining_file)

    # Check that fetch_package_details was called for each top-level package separately
    assert mock_fetch_package_details.call_count == 1
    mock_fetch_package_details.assert_any_call(["package2"])

    # Check that generate_package_summary was called for the remaining top-level package
    assert mock_generate_package_summary.call_count == 1
    mock_generate_package_summary.assert_any_call("package2", "Mock package details")

    # Verify that the generated summaries are written to the correct locations
    expected_summaries = {
        "package1/module1.py.md": "Mock summary",
        "package2/module2.py.md": "Mock summary",
        "package2/subpackage/module3.py.md": "Mock summary"
    }

    for relative_path, expected_content in expected_summaries.items():
        summary_path = os.path.join(project.package_details_folder, relative_path)
        assert os.path.exists(summary_path)
        with open(summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the package summaries are written to the correct locations
    expected_package_summaries = {
        "package1.md": "Mock package summary",
        "package2.md": "Mock package summary"
    }

    for relative_path, expected_content in expected_package_summaries.items():
        package_summary_path = os.path.join(project.package_summaries_folder, relative_path)
        assert os.path.exists(package_summary_path)
        with open(package_summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the checkpoint file is deleted after successful processing
    assert not os.path.exists(project.checkpoint_file)

@patch("se_agent.project.generate_semantic_description")
@patch("se_agent.project.generate_package_summary", return_value="Mock package summary")
@patch.object(Project, "fetch_package_details", return_value="Mock package details")
@patch.object(Project, "pull_latest_changes")
def test_update_codebase_understanding_with_partial_failures(
    mock_pull_latest,
    mock_fetch_package_details,
    mock_generate_package_summary,
    mock_generate_semantic_description,
    project_fixture
):
    project = project_fixture

    # Configure the mock to raise an exception for one of the files
    def side_effect(file_path):
        if "module2.py" in file_path:
            raise Exception("Mock error for module2.py")
        return "Mock summary"

    mock_generate_semantic_description.side_effect = side_effect

    # Call the method to update codebase understanding
    project.update_codebase_understanding()

    # Check that pull_latest_changes was called
    mock_pull_latest.assert_called_once()

    # Check that generate_semantic_description was called for each Python file
    expected_files = [
        os.path.join(project.module_src_folder, "package1/module1.py"),
        os.path.join(project.module_src_folder, "package2/module2.py"),
        os.path.join(project.module_src_folder, "package2/subpackage/module3.py")
    ]
    assert mock_generate_semantic_description.call_count == 3
    for expected_file in expected_files:
        mock_generate_semantic_description.assert_any_call(expected_file)

    # Check that fetch_package_details was called for each top-level package separately
    assert mock_fetch_package_details.call_count == 2
    mock_fetch_package_details.assert_any_call(["package1"])
    mock_fetch_package_details.assert_any_call(["package2"])

    # Verify that the generated summaries are written to the correct locations for successful files
    expected_summaries = {
        "package1/module1.py.md": "Mock summary",
        "package2/subpackage/module3.py.md": "Mock summary"
    }

    for relative_path, expected_content in expected_summaries.items():
        summary_path = os.path.join(project.package_details_folder, relative_path)
        assert os.path.exists(summary_path)
        with open(summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Verify that the package summaries are written to the correct locations
    expected_package_summaries = {
        "package1.md": "Mock package summary",
        "package2.md": "Mock package summary"
    }

    for relative_path, expected_content in expected_package_summaries.items():
        package_summary_path = os.path.join(project.package_summaries_folder, relative_path)
        assert os.path.exists(package_summary_path)
        with open(package_summary_path, "r") as f:
            content = f.read()
            assert content == expected_content

    # Check that generate_package_summary was called for the top-level packages
    assert mock_generate_package_summary.call_count == 2
    mock_generate_package_summary.assert_any_call("package1", "Mock package details")
    mock_generate_package_summary.assert_any_call("package2", "Mock package details")

    # Verify that the failing file is not in 'files_processed' but is in 'unprocessed'
    assert "package2/module2.py" not in project.checkpoint_data['files_processed']
    assert "package2" in project.checkpoint_data['unprocessed']
    assert "package2/module2.py" in project.checkpoint_data['unprocessed']["package2"]

    # Verify that the checkpoint file is saved with the correct data
    assert os.path.exists(project.checkpoint_file)
    with open(project.checkpoint_file, "r") as f:
        checkpoint_data = json.load(f)
    assert "package1/module1.py" in checkpoint_data['files_processed']
    assert "package2/module2.py" in checkpoint_data['unprocessed']["package2"]
    assert "package2/subpackage/module3.py" in checkpoint_data['files_processed']