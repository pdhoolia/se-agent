import pytest
from se_agent.project import Project
from se_agent.project_info import ProjectInfo

@pytest.mark.parametrize(
    "src_folder,package_input,expected_package_name",
    [
        # 1A: Single top-level package inside a <module-name> folder
        ("my_module", "my_module", "my_module"),
        ("my_module", "my_module/top_level_package", "top_level_package"),
        ("my_module", "my_module/top_level_package/sub_package", "top_level_package/sub_package"),

        # 1B: Multiple top-level packages inside a <module-name> folder
        ("my_module", "my_module/top_package_1", "top_package_1"),
        ("my_module", "my_module/top_package_2", "top_package_2"),

        # 2A: Single top-level package inside src/my_module
        ("src/my_module", "src/my_module", "my_module"),
        ("src/my_module", "src/my_module/top_level_package", "top_level_package"),

        # 2B: Multiple top-level packages inside src/my_module
        ("src/my_module", "src/my_module/top_package_1", "top_package_1"),
        ("src/my_module", "src/my_module/top_package_2", "top_package_2"),

        # 3: Arbitrary deeper nesting: src/x/y/my_module
        ("src/x/y/my_module", "src/x/y/my_module", "my_module"),
        ("src/x/y/my_module", "src/x/y/my_module/top_level_package", "top_level_package"),

        # 4A: Code in repo root with top-level packages
        (".", ".", "my-repo"),  # Means default package name = see test below
        (".", "top_level_package_1", "top_level_package_1"),
        (".", "top_level_package_1/sub_package", "top_level_package_1/sub_package"),
    ]
)
def test_get_package_name(src_folder, package_input, expected_package_name):
    """
    Verifies that Project.get_package_name(...) correctly strips out the src_folder path
    and returns the correct relative package name.
    """

    # Create a mock ProjectInfo
    project_info = ProjectInfo(
        repo_full_name="my-org/my-repo",
        src_folder=src_folder,
        github_token="fake-token"
    )

    # Create a Project instance
    project = Project(github_token="fake-token", projects_store="/tmp", project_info=project_info)

    # Call get_package_name
    actual_package_name = project.get_package_name(package_input)

    assert actual_package_name == expected_package_name, (
        f"Expected get_package_name('{package_input}') -> '{expected_package_name}' "
        f"when src_folder='{src_folder}' but got '{actual_package_name}'."
    )

@pytest.mark.parametrize(
    "src_folder,expected_package_name",
    [
        # If the src_folder is 'my_module', default package name => 'my_module'
        ("my_module", "my_module"),
        ("src/my_module", "my_module"),
        ("src/x/y/my_module", "my_module"),
        # If src_folder is '.' or empty, default package name => last part of repo name or "repo"
        (".", "my-repo"),
        ("", "my-repo"),  # if you allow empty string
    ]
)
def test_default_package_name(src_folder, expected_package_name):
    """
    Verifies the private method Project._get_default_package_name()
    handles 'src_folder' logic when it's '.' or other nested paths.
    """

    project_info = ProjectInfo(
        repo_full_name="my-org/my-repo",
        src_folder=src_folder,
        github_token="fake-token"
    )
    project = Project(github_token="fake-token", projects_store="/tmp", project_info=project_info)

    # Directly call _get_default_package_name
    actual = project._get_default_package_name()

    assert actual == expected_package_name, (
        f"For src_folder='{src_folder}', expected default package name '{expected_package_name}' "
        f"but got '{actual}'."
    )