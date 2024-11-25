"""Module for managing GitHub projects, including cloning repositories, updating codebase understanding, and building vector stores."""

from typing import List
import git
import json
import re
import os
import logging

from github import Github, Auth
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document

from se_agent.util.vector_store_utils import get_or_create_vector_store, DEFAULT_VECTOR_TYPE, VectorType
from se_agent.llm.api import fetch_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.project_info import ProjectInfo
from se_agent.repository_analyzer.file_analyzer import generate_semantic_description
from se_agent.repository_analyzer.package_summary import generate_package_summary

logger = logging.getLogger("se-agent")

FILES_PROCESSED = 'files_processed'
PACKAGES_PROCESSED = 'packages_processed'
UNPROCESSED = 'unprocessed'
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

    def get_vector_store(self, collection_name: str = None) -> VectorStore:
        """Retrieves or creates a vector store for the project.

        Args:
            collection_name (str, optional): Name of the collection in the vector store. Defaults to DEFAULT_VECTOR_TYPE.

        Returns:
            VectorStore: The vector store instance.
        """
        # Fetch embeddings (TODO: for the project)
        embeddings = fetch_llm_for_task(TaskName.EMBEDDING)
        # use either the specified one, or the preferred one for the project, or the default
        collection_name = collection_name or self.info.preferred_vector_type or DEFAULT_VECTOR_TYPE
        # Get or create the vector store
        vector_store = get_or_create_vector_store(embeddings, self.get_vector_store_uri(), collection_name)
        
        return vector_store

    def get_vector_store_uri(self):
        """Gets the URI for the vector store file.

        Ensures the metadata directory and vector store file exist.

        Returns:
            str: The file path to the vector store database.
        """
        # if metadata folder doesn't exist, create it
        if not os.path.exists(self.metadata_folder):
            os.makedirs(self.metadata_folder, exist_ok=True)

        # if vector db file doesn't exist, create it
        vector_db_filepath = os.path.join(self.metadata_folder, VECTOR_STORE_FILENAME)
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
            checkpoint_data = {FILES_PROCESSED: [], PACKAGES_PROCESSED: [], UNPROCESSED: {}}

        # Ensure unprocessed is initialized as a dictionary if missing
        if UNPROCESSED not in checkpoint_data:
            checkpoint_data[UNPROCESSED] = {}

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
        if not isinstance(self.checkpoint_data.get(UNPROCESSED), dict):
            self.checkpoint_data[UNPROCESSED] = {}

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint_data, f)

    def delete_checkpoint(self):
        """Deletes the checkpoint file if it exists."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        
    def clone_repository(self):
        """Clones the repository if it doesn't exist.

        Ensures the repository is added to Git's safe directories.
        """
        # Ensure the repository folder exists
        os.makedirs(self.repo_folder, exist_ok=True)

        # Check if the repository is already cloned
        if os.listdir(self.repo_folder):
            logger.info("Repository already cloned.")
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

        # Clone the repository
        logger.info(f"Cloning repository '{self.info.repo_full_name}'...")
        
        try:
            repo = self.github.get_repo(self.info.repo_full_name)

            # Prepare the local repository folder
            os.makedirs(self.repo_folder, exist_ok=True)
            logger.info(f"Using local repository folder: '{self.repo_folder}'")

            # Clone the repository
            logger.info(f"Cloning repository into '{self.repo_folder}'...")
            clone_url = repo.clone_url.replace('https://', f'https://{self.github_token}@')
            try:
                git.Repo.clone_from(clone_url, self.repo_folder)
                logger.info(f"Repository cloned successfully into '{self.repo_folder}'")
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
        
    def update_codebase_understanding(self, modified_files=None):
        """Updates the semantic understanding of the codebase.

        Summarizes only modified files or all files if none specified.

        Args:
            modified_files (list, optional): List of modified file paths. If None, all files are processed.
        """
        logger.info("Updating codebase understanding incrementally...")

        # Pull the latest changes from the repository
        self.pull_latest_changes()

        # If modified_files is None or empty, summarize all files
        if not modified_files:
            modified_files = []
            for root, _, files in os.walk(self.module_src_folder):
                for file in files:
                    if file.endswith('.py'):
                        relative_path = os.path.relpath(os.path.join(root, file), self.module_src_folder)
                        modified_files.append(relative_path)
        else:
            # Filter out non-code files from the modified files list
            modified_files = [file for file in modified_files if file.endswith('.py')]
        
        # If there are no code files to process, return early
        if not modified_files:
            logger.info("No code files modified. Skipping update.")
            return


        # Update semantic understanding for modified files
        os.makedirs(self.package_details_folder, exist_ok=True)  # where we store semantic descriptions
        semantic_summaries_vector_store = self.get_vector_store(VectorType.SEMANTIC_SUMMARY.value)
        code_files_vector_store = self.get_vector_store(VectorType.CODE.value)

        for file_path in modified_files:
            if file_path in self.checkpoint_data[FILES_PROCESSED]:
                logger.info(f"Skipping already processed file: {file_path}")
                continue

            full_file_path = os.path.join(self.module_src_folder, file_path)
            if os.path.exists(full_file_path) and file_path.endswith('.py'):
                # Determine top-level package
                if os.sep in file_path:
                    top_level_package = file_path.split(os.sep)[0]
                else:
                    # If the file is in the root of the source folder, use the source folder as top-level package
                    top_level_package = self.info.src_folder

                try:
                    with open(full_file_path, 'r') as file:
                        code = file.read()

                    if code.strip():
                        summary = generate_semantic_description(code)
                        file_doc_path = os.path.join(self.package_details_folder, file_path + ".md")
                        os.makedirs(os.path.dirname(file_doc_path), exist_ok=True)
                        with open(file_doc_path, 'w') as f:
                            f.write(summary)
                        fp = os.path.join(self.info.src_folder, file_path)
                        logger.info(f"Updated semantic summary for file: {fp}")
                        # Add to vector store
                        code_files_vector_store.add_documents(
                            documents=[Document(page_content=code, metadata={"filepath": fp})],
                            ids=[fp]
                        )
                        logger.info(f"Added code file to code vector store: {fp}")
                        semantic_summaries_vector_store.add_documents(
                            documents=[Document(page_content=summary, metadata={"filepath": fp})],
                            ids=[fp])
                        logger.info(f"Added semantic summary to code vector store: {fp}")
                    else:
                        logger.info(f"Skipped empty file: {file_path}")

                    # Mark the file as processed
                    self.checkpoint_data[FILES_PROCESSED].append(file_path)
                    self.save_checkpoint()
                except Exception as e:
                    logger.exception(f"Error summarizing file '{file_path}'")
                    # Add the file to unprocessed
                    if top_level_package not in self.checkpoint_data[UNPROCESSED]:
                        self.checkpoint_data[UNPROCESSED][top_level_package] = []
                    if file_path not in self.checkpoint_data[UNPROCESSED][top_level_package]:
                        self.checkpoint_data[UNPROCESSED][top_level_package].append(file_path)

        # Regenerate package summaries for affected top-level packages
        os.makedirs(self.package_summaries_folder, exist_ok=True)
        top_level_packages = {
            file_path.split(os.sep)[0] if os.sep in file_path else self.info.src_folder
            for file_path in modified_files
            if file_path
        }

        for package in top_level_packages:
            # Skip if the package is already processed and has no unprocessed files
            if package in self.checkpoint_data[PACKAGES_PROCESSED] and package not in self.checkpoint_data[UNPROCESSED]:
                logger.info(f"Skipping already processed package: {package}")
                continue

            try:
                package_details_content = self.fetch_package_details([package])

                if package_details_content:
                    package_summary = generate_package_summary(package, package_details_content)
                    package_summary_doc_path = os.path.join(self.package_summaries_folder, f"{package}.md")

                    # Write the generated package summary to a file
                    with open(package_summary_doc_path, "w") as package_summary_doc:
                        package_summary_doc.write(package_summary)

                    logger.info(f"Updated package summary for top-level package: {package}")
                    # Add to checkpoint
                    self.checkpoint_data[PACKAGES_PROCESSED].append(package)

                    # Clean up the unprocessed dictionary if all files are processed
                    if package in self.checkpoint_data[UNPROCESSED]:
                        for file_path in list(self.checkpoint_data[UNPROCESSED][package]):
                            if file_path in self.checkpoint_data[FILES_PROCESSED]:
                                self.checkpoint_data[UNPROCESSED][package].remove(file_path)

                        # If no unprocessed files remain, remove the package entry
                        if not self.checkpoint_data[UNPROCESSED][package]:
                            del self.checkpoint_data[UNPROCESSED][package]

                    self.save_checkpoint()
            except Exception as e:
                logger.exception(f"Error updating package summary for '{package}'.")

        # If all processing is complete, delete the checkpoint
        logger.info("Check if we can delete the checkpoint...")
        if (
            len(self.checkpoint_data[FILES_PROCESSED]) == len(modified_files)
            and len(self.checkpoint_data[PACKAGES_PROCESSED]) == len(top_level_packages)
            and not self.checkpoint_data[UNPROCESSED]
        ):
            self.delete_checkpoint()
            logger.info("Checkpoint deleted.")

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
        """Fetches all package summaries and concatenates them.

        Returns:
            str: The concatenated package summaries.
        """
        package_summaries = ""
        for item in os.listdir(self.package_summaries_folder):
            item_path = os.path.join(self.package_summaries_folder, item)
            if os.path.isfile(item_path):
                with open(item_path, 'r') as file:
                    package_summaries += file.read() + "\n\n"
        return package_summaries

    def fetch_package_details(self, packages):
        """Fetches detailed documentation for the specified packages.

        Args:
            packages (list): List of package names to fetch details for.

        Returns:
            str: The concatenated content of the package details.
        """
        package_details = ""
        for package in packages:
            package_dir = os.path.join(self.package_details_folder, package) if package != self.info.src_folder else self.package_details_folder
            if os.path.exists(package_dir):
                # Use create_hierarchical_document to collate a single document for the package
                package_details += self.create_hierarchical_document(
                    package_dir, 
                    recurse=False if package == self.info.src_folder else True
                ) + "\n\n"
        return package_details

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
            # Get the repository
            repo = self.github.get_repo(self.info.repo_full_name)
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
            repo = self.github.get_repo(self.info.repo_full_name)
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
        contents = []
        filepaths = []
        
        # Iterate over all semantic summary files in the package details folder
        for root, _, files in os.walk(self.package_details_folder):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    # Compute the relative filepath from the package_details_folder
                    relative_file_path = os.path.relpath(file_path, self.package_details_folder)
                    # Remove the .md extension
                    relative_file_path = relative_file_path[:-3]
                    # Read the summary content
                    with open(file_path, 'r') as f:
                        summary_content = f.read()
                    # Append to the list
                    contents.append(summary_content)
                    filepaths.append(os.path.join(self.info.src_folder, relative_file_path))

        # Bulk add documents to the vector store
        if filepaths:
            vector_store = self.get_vector_store(VectorType.SEMANTIC_SUMMARY.value)
            vector_store.add_documents(
                documents=[
                    Document(page_content=content, metadata={"filepath": filepath})
                    for content, filepath in zip(contents, filepaths)
                ],
                ids=filepaths
            )
            logger.info(f"Added {len(filepaths)} documents to the vector store.")
        else:
            logger.info("No documents found to add to the vector store.")

    def build_vector_store_from_code_files(self):
        """Builds the code vector store"""
        contents = []
        filepaths = []
        
        # Iterate over all code files in the module src folder
        for root, _, files in os.walk(self.module_src_folder):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Compute the relative filepath from the module_src_folder
                    relative_file_path = os.path.relpath(file_path, self.module_src_folder)
                    # Read the code file content
                    with open(file_path, 'r') as f:
                        code = f.read()
                    # Append to the list
                    contents.append(code)
                    filepaths.append(os.path.join(self.info.src_folder, relative_file_path))

        # Bulk add documents to the vector store
        if filepaths:
            vector_store = self.get_vector_store(VectorType.CODE.value)
            vector_store.add_documents(
                documents=[
                    Document(page_content=content, metadata={"filepath": filepath})
                    for content, filepath in zip(contents, filepaths)
                ],
                ids=filepaths
            )
            logger.info(f"Added {len(filepaths)} documents to the vector store.")
        else:
            logger.info("No documents found to add to the vector store.")