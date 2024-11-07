Title: Update semantic understanding of code on commits to master

Description: Our software engineering agent currently processes new issues and issue comments. It localizes them to specific packages and files, and then makes recommendations about code changes that may help fix, or enhance the code in accordance with the issue details.

To do this, it uses a large language model (LLM) to understand the code at the time of onboarding the agent to the repository. The process of code understanding results in generation of hierarchical documentation of the codebase. Two levels of documents are generated.
- **Package details**: A document is generated for each package in the module root, by recursively iterating over sub-packages and each file in the package. This document captures semantic understanding of each sub-package, and every files therein.
- **Package summaries**: Using the package details documents, a package summary document with a high-level semantic summary is generated for each package.

At the time of processing an issue, the agent uses the hierarchical documentation to first localize the issue to specific packages, then to specific files. Then the agent use the actual files from the repo to suggest code changes.

Let's now enhance the agent code to update its semantic understanding of the codebase when new commits are pushed to the master branch. Key things to note:
1. doc_generator.py generates the package details and file level semantic summary
2. package_summary_gen.py generates the package summaries
3. github_listener.py is the webhook that listens to events. It doesn't yet process any code push events.
4. project.py interfaces with the GitHub API and manages the local metadata that the agent generates and uses.