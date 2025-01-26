"""Module for managing GitHub projects, including cloning repositories, updating codebase understanding, and building vector stores."""

from typing import List, Tuple
import git
import json
import re
import os
import logging

from github import Github, Auth
from langchain_core.vectorstores import VectorStore

from se_agent.llm.api import fetch_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.project_info import ProjectInfo
from se_agent.repository_analyzer.file_analyzer import generate_semantic_description
from se_agent.repository_analyzer.package_summary import generate_package_summary
from se_agent.util.vector_store_utils import (
    get_vector_store,
    create_or_update_vector_store,
    add_documents, 
    DEFAULT_VECTOR_TYPE, 
    VectorType
)

logger = logging.getLogger("se-agent")

FILES_PROCESSED = 'files_processed'
PACKAGES_PROCESSED = 'packages_processed'
UNPROCESSED_FILES = 'unprocessed_files'
UNPROCESSED_PACKAGES = 'unprocessed_packages'
VECTOR_STORE_FILENAME = 'vector_store.db'

class Project:
    """Represents a GitHub project and provides methods to manage it.

    Attributes:
        github_token (str): GitHub authentication token.
        projects_store (str): Path to the projects storage directory.
        info (ProjectInfo): Information about the project.
        project_root_folder (str): Root directory for the project.
        repo_folder (str): Directory where the repository is cloned.
        metadata_folder (str): Directory for storing metadata.
        module_src_folder (str): Directory of the source code in the repository.
        package_details_folder (str): Directory for storing package details.
        package_summaries_folder (str): Directory for storing package summaries.
        checkpoint_file (str): Path to the checkpoint file.
        github (Github): Authenticated GitHub instance.
        checkpoint_data (dict): Data loaded from the checkpoint file.
    """
    def __init__(self, github_token: str, projects_store: str, project_info: ProjectInfo):
        """Initializes the Project instance.

        Args:
            github_token (str): GitHub authentication token.
            projects_store (str): Path to the projects storage directory.
            project_info (ProjectInfo): Information about the project.
        """
        self.github_token = project_info.github_token or github_token
        self.projects_store = projects_store
        self.info = project_info

        self.project_root_folder = os.path.join(projects_store, project_info.repo_full_name)
        self.repo_folder = os.path.join(self.project_root_folder, 'repo')
        self.metadata_folder = os.path.join(self.project_root_folder, 'metadata')
        self.module_src_folder = os.path.join(self.repo_folder, self.info.src_folder)
        self.package_details_folder = os.path.join(self.metadata_folder, 'package_details')
        self.package_summaries_folder = os.path.join(self.metadata_folder, 'package_summaries')
        self.checkpoint_file = os.path.join(self.metadata_folder, 'checkpoint.json')

        # Authenticate with GitHub
        if (project_info.api_url):
            self.github = Github(base_url=f"{self.info.api_url}", login_or_token=self.github_token)
        else:
            self.github = Github(auth=Auth.Token(self.github_token))

        # Load checkpoint data if it exists
        self.checkpoint_data = self.load_checkpoint()

    def get_github_instance(self) -> Github:
        """Returns an authenticated Github instance."""
        if self.info.api_url:
            return Github(base_url=f"{self.info.api_url}", login_or_token=self.github_token)
        else:
            return Github(auth=Auth.Token(self.github_token))

    def get_vector_store(self, prefix: str = None) -> VectorStore:
        """Retrieves or creates a vector store for the project.

        Args:
            collection_name (str, optional): Name of the collection in the vector store. Defaults to DEFAULT_VECTOR_TYPE.

        Returns:
            VectorStore: The vector store instance.
        """
        # Fetch embeddings (TODO: for the project)
        embeddings = fetch_llm_for_task(TaskName.EMBEDDING)
        # use either the specified one, or the preferred one for the project, or the default
        prefix = prefix or self.info.preferred_vector_type or DEFAULT_VECTOR_TYPE
        # Get or create the vector store
        vector_store = get_vector_store(embeddings, self.get_vector_store_uri(prefix))
        
        return vector_store

    def get_vector_store_uri(self, prefix: str = None) -> str:
        """Gets the URI for the vector store file.

        Ensures the metadata directory and vector store file exist.

        Returns:
            str: The file path to the vector store database.
        """
        # if metadata folder doesn't exist, create it
        if not os.path.exists(self.metadata_folder):
            os.makedirs(self.metadata_folder, exist_ok=True)

        # if vector db file doesn't exist, create it
        vector_db_filepath = os.path.join(self.metadata_folder, f"{prefix}_{VECTOR_STORE_FILENAME}" if prefix else VECTOR_STORE_FILENAME)
        if not os.path.exists(vector_db_filepath):
            open(vector_db_filepath, 'w').close()

        return vector_db_filepath

    def load_checkpoint(self):
        """Loads checkpoint data from the checkpoint file if it exists.

        Returns:
            dict: The loaded checkpoint data.
        """
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
        else:
            checkpoint_data = {FILES_PROCESSED: [], PACKAGES_PROCESSED: [], UNPROCESSED_FILES: {}, UNPROCESSED_PACKAGES: {}}

        # Ensure unprocessed_files is initialized as a dictionary if missing
        if UNPROCESSED_FILES not in checkpoint_data:
            checkpoint_data[UNPROCESSED_FILES] = {}

        # Ensure unprocessed_packages is initialized as a dictionary if missing
        if UNPROCESSED_FILES not in checkpoint_data:
            checkpoint_data[UNPROCESSED_FILES] = {}

        # Ensure FILES_PROCESSED and PACKAGES_PROCESSED are lists
        if not isinstance(checkpoint_data.get(FILES_PROCESSED), list):
            checkpoint_data[FILES_PROCESSED] = []
        if not isinstance(checkpoint_data.get(PACKAGES_PROCESSED), list):
            checkpoint_data[PACKAGES_PROCESSED] = []

        return checkpoint_data

    def save_checkpoint(self):
        """Saves the current checkpoint data to the checkpoint file."""
        # Validate data before saving
        if not isinstance(self.checkpoint_data.get(FILES_PROCESSED), list):
            self.checkpoint_data[FILES_PROCESSED] = []
        if not isinstance(self.checkpoint_data.get(PACKAGES_PROCESSED), list):
            self.checkpoint_data[PACKAGES_PROCESSED] = []
        if not isinstance(self.checkpoint_data.get(UNPROCESSED_FILES), dict):
            self.checkpoint_data[UNPROCESSED_FILES] = {}
        if not isinstance(self.checkpoint_data.get(UNPROCESSED_PACKAGES), dict):
            self.checkpoint_data[UNPROCESSED_PACKAGES] = {}

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint_data, f)

    def delete_checkpoint(self):
        """Deletes the checkpoint file if it exists."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        
    def is_cloned(self):
        """Checks if the repository is already cloned.

        Returns:
            bool: True if the repository is already cloned, False otherwise.
        """
        return os.path.exists(self.repo_folder) and os.listdir(self.repo_folder)

    def clone_repository(self, requires_safe_directory: bool = True, requires_auth: bool = True):
        """Clones the repository if it doesn't exist.

        Ensures the repository is added to Git's safe directories.
        """
        # Ensure the repository folder exists
        os.makedirs(self.repo_folder, exist_ok=True)

        # Check if the repository is already cloned
        if self.is_cloned():
            logger.info("Repository already cloned.")
            if requires_safe_directory:
                git_cmd = git.cmd.Git()
                try:
                    safe_directories = git_cmd.config('--global', '--get-all', 'safe.directory').splitlines()
                except git.GitCommandError:
                    # If the command fails, assume no safe directories are set
                    safe_directories = []
                # Add to safe directories if not already present
                if self.repo_folder not in safe_directories:
                    git_cmd.config('--global', '--add', 'safe.directory', self.repo_folder)
                    logger.info(f"Safe directory added: {self.repo_folder}")
            return
        
        try:
            if requires_auth:
                github = self.get_github_instance()
                repo = github.get_repo(self.info.repo_full_name)
                clone_url = repo.clone_url
                clone_url = clone_url.replace('https://', f'https://{self.github_token}@')
            else:
                clone_url = f"https://github.com/{self.info.repo_full_name}.git"

            # Prepare the local repository folder
            os.makedirs(self.repo_folder, exist_ok=True)

            # Clone the repository
            logger.info(f"Cloning repository {self.info.repo_full_name} into '{self.repo_folder}'...")
            try:
                git.Repo.clone_from(clone_url, self.repo_folder)
                logger.info(f"Repository cloned successfully.")
                if requires_safe_directory:
                    git.cmd.Git().config('--global', '--add', 'safe.directory', self.repo_folder)
                    logger.info(f"Safe directory added: {self.repo_folder}")
            except Exception as e:
                logger.error(f"Error cloning repository: {e}")
                raise
        except Exception as e:
            logger.error(f"Error accessing repository: {e}")
            raise

    def pull_latest_changes(self):
        """Pulls the latest changes from the main branch of the repository."""
        logger.info("Pulling latest changes from main branch...")
        try:
            repo = git.Repo(self.repo_folder)
            origin = repo.remotes.origin
            origin.pull(self.info.main_branch)
            logger.info("Latest changes pulled from main branch.")
        except Exception as e:
            logger.error(f"Error pulling latest changes: {e}")
            raise
        
    def get_current_commit(self):
        """Fetches the current commit hash for the repository.

        Returns:
            str: The current commit hash.
        """
        try:
            repo = git.Repo(self.repo_folder)
            current_commit = repo.head.commit.hexsha
            logger.info(f"Current commit hash: {current_commit}")
            return current_commit
        except Exception as e:
            logger.error(f"Error fetching the current commit hash: {e}")
            raise

    def reset_to_commit(self, commit_hash):
        """Resets the repository to a specific commit hash.

        Args:
            commit_hash (str): The commit hash to reset to.
        """
        try:
            repo = git.Repo(self.repo_folder)
            repo.git.reset('--hard', commit_hash)
            logger.info(f"Repository reset to commit {commit_hash}.")
        except Exception as e:
            logger.error(f"Error resetting repository to commit {commit_hash}: {e}")
            raise

    def update_codebase_understanding(self, modified_files=None):
        """Updates the semantic understanding of the codebase.

        Orchestrates generating semantic summaries, higher order package summaries
        and updating vector stores.

        Args:
            modified_files (list, optional): List of modified file paths. If None, all files are processed.
        """
        logger.info("Updating codebase understanding incrementally...")

        # Pull the latest changes from the repository
        self.pull_latest_changes()

        # Step 1: Generate semantic summaries
        _, all_processed_files = self.generate_semantic_summaries(modified_files)

        # Step 2: Regenerate package summaries
        top_level_packages = self.get_top_level_packages(all_processed_files)
        self.generate_package_summaries(top_level_packages)

        # Step 3: Update file-level vector stores
        self.update_vector_store(VectorType.CODE, all_processed_files)
        self.update_vector_store(VectorType.SEMANTIC_SUMMARY, all_processed_files)

        # Step 4: if we are here, process has not been interrupted. delete checkpoint
        self.delete_checkpoint()
        logger.info("Processing complete. Checkpoint deleted.")

    def generate_semantic_summaries(self, modified_files: List[str] = None) -> Tuple[List[str], List[str]]:
        """Generates semantic summaries for the specified files.

        Args:
            modified_files (List[str], optional): List of modified file paths. If None, all files are processed.

        Returns:
            Tuple[List[str], List[str]]:
                - List of files processed in the current run.
                - List of all processed files (cumulative).
        """
        if not modified_files:
            # Default to all .py files in the module source folder
            modified_files = [
                os.path.relpath(os.path.join(root, file), self.module_src_folder)
                for root, _, files in os.walk(self.module_src_folder)
                for file in files if file.endswith('.py')
            ]

        # Filter out already processed files
        files_to_process = [
            file for file in modified_files
            if file not in self.checkpoint_data[FILES_PROCESSED]
        ]
        logger.info(f"Skipping already processed files: {self.checkpoint_data[FILES_PROCESSED]}.")

        if not files_to_process:
            logger.info("No new files to process for semantic summaries.")
            return [], self.checkpoint_data[FILES_PROCESSED]

        os.makedirs(self.package_details_folder, exist_ok=True)  # Ensure output directory exists

        processed_files = []
        for file_path in files_to_process:
            full_file_path = os.path.join(self.module_src_folder, file_path)
            try:
                if os.path.exists(full_file_path):
                    with open(full_file_path, 'r') as file:
                        code = file.read()

                    if code.strip():
                        summary = generate_semantic_description(code)
                        summary_file_path = os.path.join(self.package_details_folder, f"{file_path}.md")
                        os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
                        with open(summary_file_path, 'w') as summary_file:
                            summary_file.write(summary)
                        processed_files.append(file_path)
                        logger.info(f"Generated semantic summary for: {file_path}")

                        # Update and save checkpoint after successful processing
                        self.checkpoint_data[FILES_PROCESSED].append(file_path)
                        self.save_checkpoint()
                    else:
                        logger.info(f"Skipped empty file: {file_path}")
                else:
                    logger.warning(f"File not found: {file_path}")
            except Exception as e:
                logger.exception(f"Error generating semantic summary for '{file_path}': {e}")
                self.checkpoint_data['unprocessed_files'][file_path] = str(e)
                self.save_checkpoint()

        # Return both newly processed files and all processed files
        all_processed_files = self.checkpoint_data[FILES_PROCESSED]
        return processed_files, all_processed_files

    def get_top_level_packages(self, file_paths: List[str]) -> List[str]:
        """Identifies top-level packages affected by the given file paths.

        Args:
            file_paths (List[str]): List of file paths.

        Returns:
            List[str]: List of top-level package names.
        """
        top_level_packages = set()
        for file_path in file_paths:
            if os.sep in file_path:
                top_level_package = file_path.split(os.sep)[0]
            else:
                top_level_package = self._get_default_package_name()
            top_level_packages.add(top_level_package)
        return list(top_level_packages)
    
    def generate_package_summaries(self, top_level_packages: List[str]):
        """Regenerates package summaries for the specified top-level packages.

        Args:
            top_level_packages (List[str]): List of top-level package names.
        """
        logger.info(f"Regenerating package summaries for packages: {top_level_packages}")
        os.makedirs(self.package_summaries_folder, exist_ok=True)

        for package in top_level_packages:
            try:
                # Fetch package details
                package_details = self.fetch_package_details([package])

                # Generate summary if details are available
                if package_details:
                    package_summary = generate_package_summary(package, package_details)
                    # Get the package name without the src_folder path
                    package_name = self.get_package_name(package)
                    summary_path = os.path.join(self.package_summaries_folder, f"{package_name}.md")

                    # Write the summary to a file
                    with open(summary_path, 'w') as summary_file:
                        summary_file.write(package_summary)
                    logger.info(f"Generated package summary for package: {package_name}")

                    # Update and save checkpoint after successful processing
                    if package not in self.checkpoint_data[PACKAGES_PROCESSED]:
                        self.checkpoint_data[PACKAGES_PROCESSED].append(package)
                    self.save_checkpoint()
            except Exception as e:
                logger.exception(f"Error generating package summary for package '{package}': {e}")
                # Record unprocessed packages with exceptions
                self.checkpoint_data['unprocessed_packages'][package] = str(e)
                self.save_checkpoint()

    def get_package_name(self, package):
        if package == self._get_default_package_name():
            return package
        return os.path.relpath(package, self.info.src_folder)

    def _get_default_package_name(self):
        if self.info.src_folder and self.info.src_folder != '.':
            return self.info.src_folder.split('/')[-1].strip()
        else:
            return self.info.repo_full_name.split('/')[-1].strip()

    def update_vector_store(self, vector_type: VectorType, file_paths: List[str]) -> None:
        """Updates the specified vector store with new documents.

        Args:
            vector_type (VectorType): The type of vector store to update (e.g., CODE or SEMANTIC_SUMMARY).
            file_paths (List[str]): List of file paths to add to the vector store.
        """
        if not file_paths:
            logger.info(f"No files to update for vector store: {vector_type.value}")
            return

        vector_store = self.get_vector_store(vector_type.value)
        contents = []
        metadata_filepaths = []

        for file_path in file_paths:
            full_file_path = os.path.join(
                self.package_details_folder if vector_type == VectorType.SEMANTIC_SUMMARY else self.module_src_folder,
                file_path + (".md" if vector_type == VectorType.SEMANTIC_SUMMARY else "")
            )

            try:
                with open(full_file_path, 'r') as f:
                    contents.append(f.read())
                metadata_filepaths.append(os.path.join(self.info.src_folder, file_path))
            except Exception as e:
                logger.warning(f"Failed to read file for vector store: {full_file_path}, error: {e}")

        if contents and metadata_filepaths:
            add_documents(
                contents=contents,
                filepaths=metadata_filepaths, 
                uri=self.get_vector_store_uri(vector_type.value),
                embeddings=vector_store.embeddings)
            logger.info(f"Updated {vector_type.value} vector store with {len(metadata_filepaths)} files.")
        else:
            logger.info(f"No valid content to add to {vector_type.value} vector store.")
    
    def onboard(self):
        """Performs the initial onboarding of the project.

        Clones the repository and updates the codebase understanding.
        """
        self.clone_repository()
        self.update_codebase_understanding()
        logger.info("Project onboarded successfully!")

    def create_hierarchical_document(self, root_folder, recurse=True):
        """Creates a hierarchical document for a package based on semantic descriptions.

        Args:
            root_folder (str): The root folder containing the semantic descriptions of the package.
            recurse (bool, optional): Whether to recurse into sub-packages. Defaults to True.

        Returns:
            str: A hierarchical document for the entire package.
        """
        def modify_headers(content: str, header_offset: str) -> str:
            """Prefixes all markdown headers with the given header offset.

            Args:
                content (str): The content to modify.
                header_offset (str): The header offset string (e.g., '##').

            Returns:
                str: The content with modified headers.
            """
            
            modified_content = re.sub(r'(#+)', lambda match: header_offset + match.group(0), content)
            return modified_content
        
        def build_document(current_folder, level, recurse=True):
            """Recursively builds the hierarchical document.

            Args:
                current_folder (str): The current folder being processed.
                level (int): The current header level.
                recurse (bool, optional): Whether to recurse into sub-packages. Defaults to True.

            Returns:
                str: The document content for the current folder.
            """
            document = ""
            header_prefix = "#" * level

            # to get package name, let's get the part relative to the self.package_details_folder
            # if '.', use self.info.src_folder
            # else use replace all os.sep with '.' and use that
            package_name = os.path.relpath(current_folder, self.package_details_folder)
            if package_name == '.':
                package_name = self.info.src_folder
            else:
                package_name = package_name.replace(os.sep, '.')

            # Add heading for the current package
            document += f"{header_prefix} {package_name}\n\n"

            # Add descriptions for all files in the current package
            for filename in sorted(os.listdir(current_folder)):
                file_path = os.path.join(current_folder, filename)
                if os.path.isfile(file_path) and filename.endswith('.md'):
                    # Extract semantic description
                    with open(file_path, 'r') as file:
                        file_content = file.read()

                    # Add heading for the file and adjust header offset
                    file_name_without_ext = os.path.splitext(filename)[0]
                    document += f"{header_prefix}# {file_name_without_ext}\n\n"
                    adjusted_content = modify_headers(file_content, "#" * (level + 1))
                    document += f"{adjusted_content}\n\n"

            # Recursively add descriptions for all sub-packages
            if recurse:
                for sub_folder in sorted(os.listdir(current_folder)):
                    sub_folder_path = os.path.join(current_folder, sub_folder)
                    if os.path.isdir(sub_folder_path):
                        document += build_document(sub_folder_path, level + 1)

            return document

        # Start building the document from the root folder
        return build_document(root_folder, 1, recurse=recurse)
    
    def fetch_package_summaries(self):
        """Fetches all package summaries and concatenates them, along with returning the list of package names.

        Returns:
            Tuple[str, List[str]]: The concatenated package summaries and the list of package names.
        """
        package_summaries = ""
        package_names = []
        for item in os.listdir(self.package_summaries_folder):
            item_path = os.path.join(self.package_summaries_folder, item)
            if os.path.isfile(item_path):
                with open(item_path, 'r') as file:
                    package_summaries += file.read() + "\n\n"
                package_names.append(item.replace('.md', ''))
        return package_summaries, package_names

    def fetch_package_details(self, packages):
        """
        Fetches detailed documentation for the specified packages by assembling
        a hierarchical document of each package's .md files (and its subfolders).
        """
        package_details = ""

        for pkg in packages:
            # Figure out where the .md files actually live
            if pkg == self._get_default_package_name():
                # Means it's effectively '.' or root, so .md files live directly under package_details/
                package_dir = self.package_details_folder
                # Typically we don't want to recurse at the root if you're treating the root as a single "package."
                # But it's up to you; you can set 'recurse=True' if that’s what you want:
                do_recurse = False
            else:
                package_dir = os.path.join(self.package_details_folder, pkg)
                do_recurse = True  # For top-level packages, you might want to gather sub-packages too.

            if not os.path.exists(package_dir):
                logger.warning(f"No package_details folder found at: {package_dir}. Skipping.")
                continue

            # 3. Build a hierarchical document from package_dir
            details_for_this_package = self.create_hierarchical_document(package_dir, recurse=do_recurse)
            package_details += details_for_this_package + "\n\n"

        return package_details

    def get_package(self, filename: str) -> str:
        """
        Returns the top-level package name that contains the filename.

        Top-level packages are:
            - either self.info.src_folder.split('/')[-1], if the file is found directly in self.module_src_folder
            - or the name of the folder if it is found (recursively) within one of the direct child folders of the self.module_src_folder

        Args:
            filename (str): Name of the file.

        Returns:
            str: Name of the package that contains the resource.
        """
        for root, dirs, files in os.walk(self.module_src_folder):
            if filename in files:
                # Determine the package path relative to src folder
                relative_path = os.path.relpath(root, self.module_src_folder)
                package_parts = relative_path.split(os.sep)

                # If the file is found directly under src_folder
                if not relative_path or relative_path == '.':
                    return self._get_default_package_name()

                # Otherwise, return the top-level directory
                return package_parts[0]

        return None

    def fetch_code_files(self, filepaths: List[str]):
        """Retrieves the contents of the specified code files.

        Args:
            filepaths (List[str]): List of file paths relative to the module source folder.

        Returns:
            List[str]: List of file contents.
        """
        files = []
        for filepath in filepaths:
            full_filepath = os.path.join(self.repo_folder, filepath)
            
            if os.path.exists(full_filepath):
                with open(full_filepath, 'r') as f:
                    file_content = f.read()
                    files.append(file_content)
        return files
        
    def post_issue_comment(self, issue_number, comment_body):
        """Posts a comment on a GitHub issue.

        Args:
            issue_number (int): The number of the issue.
            comment_body (str): The body of the comment to post.
        """
        try:
            github = self.get_github_instance()
            # Get the repository
            repo = github.get_repo(self.info.repo_full_name)
            # Get the issue
            issue = repo.get_issue(number=issue_number)
            # Post the comment
            issue.create_comment(body=comment_body)
            logger.info(f"Comment posted to issue #{issue_number}")
        except Exception as e:
            logger.error(f"Error posting comment to GitHub: {e}")
            raise

    def fetch_issue_comments(self, issue_number):
        """Fetches the comments on a GitHub issue.

        Args:
            issue_number (int): The number of the issue.

        Returns:
            list: List of dictionaries containing user login and comment body.
        """
        try:
            github = self.get_github_instance()
            repo = github.get_repo(self.info.repo_full_name)
            issue = repo.get_issue(number=issue_number)
            comments = []
            for comment in issue.get_comments():
                comments.append({
                    'user': {
                        'login': comment.user.login
                    },
                    'body': comment.body
                })
            return comments
        except Exception as e:
            logger.error(f"Error fetching issue comments: {e}")
            raise

    def build_vector_store_from_existing_summaries(self):
        """Builds the vector store by reading existing semantic summaries."""
        try:
            create_or_update_vector_store(
                source_dir=self.package_details_folder,
                uri=self.get_vector_store_uri(),
                embeddings=fetch_llm_for_task(TaskName.EMBEDDING),
                path_prefix=self.info.src_folder
            )
            logger.info("Vector store for semantic summaries created successfully.")
        except Exception as e:
            logger.error(f"Failed to create vector store from semantic summaries: {e}")
            raise

    def build_vector_store_from_code_files(self):
        """Builds the code vector store"""
        try:
            create_or_update_vector_store(
                source_dir=self.module_src_folder,
                uri=self.get_vector_store_uri(),
                embeddings=fetch_llm_for_task(TaskName.EMBEDDING),
                path_prefix=self.info.src_folder
            )
            logger.info("Vector store for code files created successfully.")
        except Exception as e:
            logger.error(f"Failed to create vector store from code files: {e}")
            raise