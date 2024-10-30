import os
import pytest
from unittest.mock import patch, mock_open
from se_agent.project import Project
from se_agent.project_info import ProjectInfo

@pytest.fixture
def project_info():
    return ProjectInfo(
        github_token='test_token',
        api_url=None,
        repo_full_name='owner/repo-name',
        src_folder='src'
    )

@pytest.fixture
def project(tmp_path, project_info):
    projects_store = tmp_path / "projects_store"
    projects_store.mkdir()
    return Project('test_github_token', str(projects_store), project_info)

@patch("os.path.isdir")
@patch("os.path.isfile")
@patch("os.path.exists")
@patch("os.listdir")
@patch("builtins.open", new_callable=mock_open, read_data="### File Summary\nContent of the file.")
def test_fetch_package_details(mock_open, mock_listdir, mock_exists, mock_isfile, mock_isdir, project):
    # Set up the package directory structure in the mocked filesystem
    package_details_path1 = os.path.join(project.package_details_folder, "package1")
    package_details_path2 = os.path.join(project.package_details_folder, "package2")
    subpackage_details_path = os.path.join(package_details_path2, "subpackage")

    # Set up the mocked behavior
    mock_exists.side_effect = lambda x: x in [
        project.package_details_folder,
        package_details_path1,
        package_details_path2,
        subpackage_details_path,
        os.path.join(package_details_path1, "file1.py.md"),
        os.path.join(package_details_path1, "file2.py.md"),
        os.path.join(subpackage_details_path, "file3.py.md")
    ]
    mock_isfile.side_effect = lambda x: x in [
        os.path.join(package_details_path1, "file1.py.md"),
        os.path.join(package_details_path1, "file2.py.md"),
        os.path.join(subpackage_details_path, "file3.py.md")
    ]
    mock_listdir.side_effect = lambda x: (
        ["package1", "package2"] if x == project.package_details_folder else
        ["file1.py.md", "file2.py.md"] if x == package_details_path1 else
        ["subpackage"] if x == package_details_path2 else
        ["file3.py.md"] if x == subpackage_details_path else
        []
    )
    mock_isdir.side_effect = lambda x: x in [package_details_path1, package_details_path2, subpackage_details_path]

    # Call the method
    result = project.fetch_package_details(["package1", "package2"])

    # Assertions for package1
    assert "# package1" in result
    assert "## file1.py" in result
    assert "## file2.py" in result
    assert "Content of the file." in result
    
    # Assertions for package2
    assert "# package2" in result
    assert "## package2.subpackage" in result
    assert "### file3.py" in result
    
    # Ensure files were opened correctly
    mock_open.assert_any_call(os.path.join(package_details_path1, "file1.py.md"), "r")
    mock_open.assert_any_call(os.path.join(package_details_path1, "file2.py.md"), "r")
    mock_open.assert_any_call(os.path.join(subpackage_details_path, "file3.py.md"), "r")
