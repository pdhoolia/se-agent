import pytest
import os
from unittest.mock import patch, MagicMock
from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.repository_analyzer.package_summary import generate_package_summary

@pytest.mark.parametrize(
    "src_folder,packages,expected_summary_files",
    [
        # Case 1: <module-name> with two top-level packages + direct code files
        (
            "my_module",
            ["my_module/top_package_1", "my_module/top_package_2", "my_module"],
            ["top_package_1.md", "top_package_2.md", "my_module.md"]
        ),
        # Case 2: src/my_module with one top-level package
        (
            "src/my_module",
            ["src/my_module/top_package"],
            ["top_package.md"]
        ),
        # Case 3: code in repo root with multiple top-level packages
        (
            ".",
            ["top_level_package_1", "top_level_package_2", "."],
            ["top_level_package_1.md", "top_level_package_2.md", "my-repo.md"]
        ),
    ]
)
@patch('se_agent.repository_analyzer.package_summary.call_llm_for_task')
def test_generate_summaries_for_various_layouts(
    mock_llm_call,
    src_folder,
    packages,
    expected_summary_files,
    tmp_path
):
    """
    Integration-style test that checks whether the final summary file names (and paths)
    match what we expect for different src_folder layouts.
    """
    # Mock LLM return
    mock_llm_call.return_value.content = "```python\nThis is a package summary.\n```"

    # 1. Set up a Project with the given src_folder, using a tmp_path as projects_store
    repo_full_name = "my-org/my-repo"
    project_info = ProjectInfo(
        repo_full_name=repo_full_name,
        src_folder=src_folder,
        github_token="fake-token"
    )
    project = Project(
        github_token="fake-token",
        projects_store=str(tmp_path),
        project_info=project_info
    )
    
    # 2. We'll assume that "package_details" already has *some* MD content
    #    For simplicity, let’s just pretend each package has non-empty string data.
    #    In real usage, we'd have generated semantic summary files in metadata/package_details.
    package_details = "Some existing package details content..."

    # Create the "package_summaries_folder"
    os.makedirs(project.package_summaries_folder, exist_ok=True)

    # 3. For each package, generate a summary file. 
    #    We won't re-test all logic in "generate_package_summary" because that's tested elsewhere,
    #    but we want to confirm the final file name uses get_package_name(...) properly.
    for pkg in packages:
        summarized_text = generate_package_summary(pkg, package_details)
        # Now we do the final step that project.generate_package_summaries(...) would do:
        package_name = project.get_package_name(pkg)
        summary_path = os.path.join(project.package_summaries_folder, f"{package_name}.md")
        with open(summary_path, 'w') as summary_file:
            summary_file.write(summarized_text)

    # 4. Verify that the expected summary files exist in the project.package_summaries_folder
    actual_files = sorted(os.listdir(project.package_summaries_folder))
    assert len(actual_files) == len(expected_summary_files), (
        f"Expected {len(expected_summary_files)} summary file(s) but found {len(actual_files)}: {actual_files}"
    )

    for exp in expected_summary_files:
        assert exp in actual_files, f"Expected summary file '{exp}' was not created. Actual: {actual_files}"


def test_single_files_in_repo_root(tmp_path):
    """
    Test how a single code file at the repo root leads to 'repo.md' or <repo-name>.md summary.
    """
    repo_name = "my-repo"
    src_folder = "."
    project_info = ProjectInfo(
        repo_full_name=f"my-org/{repo_name}",
        src_folder=src_folder,
        github_token="fake-token"
    )
    project = Project(
        github_token="fake-token",
        projects_store=str(tmp_path),
        project_info=project_info
    )
    # Suppose we have a file 'main.py' in the root
    # and a top-level package 'top_pkg'
    packages = [".", "top_pkg"]  # '.' means the root
    
    # For brevity, just do the same snippet:
    package_details = "Fake details..."
    os.makedirs(project.package_summaries_folder, exist_ok=True)

    for pkg in packages:
        summary_content = "```python\nThis is a root or package summary.\n```"
        package_name = project.get_package_name(pkg)
        summary_path = os.path.join(project.package_summaries_folder, f"{package_name}.md")
        with open(summary_path, 'w') as f:
            f.write(summary_content)

    # Now check that the file for '.' is named 'my-repo.md'
    actual_files = os.listdir(project.package_summaries_folder)
    assert "my-repo.md" in actual_files, f"Expected 'my-repo.md' in {actual_files}"
    assert "top_pkg.md" in actual_files, f"Expected 'top_pkg.md' in {actual_files}"