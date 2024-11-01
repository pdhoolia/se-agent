import git
import json
import logging
import re
import os

from github import Github, Auth

from se_agent.project_info import ProjectInfo
from se_agent.repository_analyzer.file_analyzer import generate_semantic_description
from se_agent.repository_analyzer.package_summary import generate_package_summary

FILES_PROCESSED = 'files_processed'
PACKAGES_PROCESSED = 'packages_processed'
UNPROCESSED = 'unprocessed'

class Project:
    def __init__(self, github_token, projects_store, project_info: ProjectInfo):
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

        # Set up logging
        self.logger = logging.getLogger(self.info.repo_full_name)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        self.logger.addHandler(handler)

        # Load checkpoint data if it exists
        self.checkpoint_data = self.load_checkpoint()

    def load_checkpoint(self):
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
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
    
    def clone_repository(self):
        # Clone the repository
        self.logger.info(f"Cloning repository '{self.info.repo_full_name}'...")
        try:
            repo = self.github.get_repo(self.info.repo_full_name)

            # Prepare the local repository folder
            os.makedirs(self.repo_folder, exist_ok=True)
            self.logger.info(f"Using local repository folder: '{self.repo_folder}'")

            # Clone the repository
            self.logger.info(f"Cloning repository into '{self.repo_folder}'...")
            clone_url = repo.clone_url.replace('https://', f'https://{self.github_token}@')
            try:
                if os.listdir(self.repo_folder):
                    self.logger.info("Repository already cloned.")
                else:
                    git.Repo.clone_from(clone_url, self.repo_folder)
                    self.logger.info(f"Repository cloned successfully into '{self.repo_folder}'")
            except Exception as e:
                self.logger.error(f"Error cloning repository: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Error accessing repository: {e}")
            raise

    def pull_latest_changes(self):
        """ Pull the latest changes from the main branch """
        self.logger.info("Pulling latest changes from main branch...")
        try:
            repo = git.Repo(self.repo_folder)
            origin = repo.remotes.origin
            origin.pull(self.info.main_branch)
            self.logger.info("Latest changes pulled from main branch.")
        except Exception as e:
            self.logger.error(f"Error pulling latest changes: {e}")
            raise
    
    def update_codebase_understanding(self, modified_files=None):
        """
        Update semantic understanding of the codebase by summarizing only modified files.
        """
        self.logger.info("Updating codebase understanding incrementally...")

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

        # Update semantic understanding for modified files
        for file_path in modified_files:
            if file_path in self.checkpoint_data[FILES_PROCESSED]:
                self.logger.info(f"Skipping already processed file: {file_path}")
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
                    summary = generate_semantic_description(full_file_path)
                    if summary is not None:
                        file_doc_path = os.path.join(self.package_details_folder, file_path + ".md")
                        os.makedirs(os.path.dirname(file_doc_path), exist_ok=True)
                        with open(file_doc_path, 'w') as f:
                            f.write(summary)
                        self.logger.info(f"Updated semantic summary for file: {file_path}")
                    else:
                        self.logger.info(f"File is empty, no summary generated for file: {file_path}")

                    # Mark the file as processed
                    self.checkpoint_data[FILES_PROCESSED].append(file_path)
                    self.save_checkpoint()
                except Exception as e:
                    self.logger.exception(f"Error summarizing file '{file_path}'")
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
                self.logger.info(f"Skipping already processed package: {package}")
                continue

            try:
                package_details_content = self.fetch_package_details([package])

                if package_details_content:
                    package_summary = generate_package_summary(package, package_details_content)
                    package_summary_doc_path = os.path.join(self.package_summaries_folder, f"{package}.md")

                    # Write the generated package summary to a file
                    with open(package_summary_doc_path, "w") as package_summary_doc:
                        package_summary_doc.write(package_summary)

                    self.logger.info(f"Updated package summary for top-level package: {package}")
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
                self.logger.exception(f"Error updating package summary for '{package}'.")

        # If all processing is complete, delete the checkpoint
        self.logger.info("Check if we can delete the checkpoint...")
        if (
            len(self.checkpoint_data[FILES_PROCESSED]) == len(modified_files)
            and len(self.checkpoint_data[PACKAGES_PROCESSED]) == len(top_level_packages)
            and not self.checkpoint_data[UNPROCESSED]
        ):
            self.delete_checkpoint()
            self.logger.info("Checkpoint deleted.")

    def onboard(self):
        self.clone_repository()
        self.update_codebase_understanding()
        self.logger.info("Project onboarded successfully!")

    def create_hierarchical_document(self, root_folder, recurse=True):
        """
        Create a hierarchical document for a package based on semantic descriptions of individual files.

        Args:
            root_folder (str): The root folder containing the semantic descriptions of the package.

        Returns:
            str: A hierarchical document for the entire package.
        """
        def modify_headers(content: str, header_offset: str) -> str:
            """Prefix all markdown headers with the given headerOffset."""
            
            modified_content = re.sub(r'(#+)', lambda match: header_offset + match.group(0), content)
            return modified_content
        
        def build_document(current_folder, level, recurse=True):
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
        package_summaries = ""
        for item in os.listdir(self.package_summaries_folder):
            item_path = os.path.join(self.package_summaries_folder, item)
            if os.path.isfile(item_path):
                with open(item_path, 'r') as file:
                    package_summaries += file.read() + "\n\n"
        return package_summaries

    def fetch_package_details(self, packages):
        """
        Fetches the detailed documentation for the specified packages and returns the content as a string.
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

    def fetch_code_files(self, file_suggestions):
        """Get the contents of the files suggested by the AI model."""
        files = []
        src_path = self.info.src_folder
        for package, filename in file_suggestions:
            # Ensure the package path starts with src_path
            if not package.startswith(src_path):
                package_path = os.path.join(src_path, package)
            else:
                package_path = package

            # Split the package by os.sep to check the last part of the package
            package_parts = package.split(os.sep)
            filename_without_extn, extn = os.path.splitext(filename)
            
            # Check if the last part of the package matches the filename (without extn)
            if package_parts[-1] == filename_without_extn:
                # The file should be located at x/y/z.extn instead of x/y/z/z.extn
                file_path = os.path.join(self.repo_folder, package_path + extn)
                full_file_name = package_path + extn
            else:
                # Default behavior
                file_path = os.path.join(self.repo_folder, package_path, filename)
                full_file_name = os.path.join(package_path, filename)
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    file_content = f.read()
                    files.append((full_file_name, file_content))
        return files
    
    def post_issue_comment(self, issue_number, comment_body):
        """Post a comment on a GitHub issue."""
        try:
            # Get the repository
            repo = self.github.get_repo(self.info.repo_full_name)
            # Get the issue
            issue = repo.get_issue(number=issue_number)
            # Post the comment
            issue.create_comment(body=comment_body)
            self.logger.info(f"Comment posted to issue #{issue_number}")
        except Exception as e:
            self.logger.error(f"Error posting comment to GitHub: {e}")
            raise

    def fetch_issue_comments(self, issue_number):
        """Fetches the comments on an issue."""
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
            self.logger.error(f"Error fetching issue comments: {e}")
            raise
