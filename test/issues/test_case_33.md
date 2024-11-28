SWE-bench provides datasets to evaluate software engineering agents.

Each evaluation task instance (mapping to our concept of issue) provides:
1. repo: mapping to our repo_full_name
2. instance_id: mapping to our issue
3. problem_statement: mapping to our issue body
4. patch: mapping to the combination of our localization & change suggestions

Following challenges need to be addressed to evaluate our agent using the SWE-bench dataset:

1. **Our agent needs to be added as a collaborator on the repo**. However, SWE-bench is for offline evaluation. To address this we should be able to construct a Project with a pre-cloned repository as well.
    1. Project should not keep `Github` as a member (requiring authenticating with GitHub at the time of construction)
    2. Let's add another function in Project that returns an authenticated `Github` object.
    3. Functions (e.g., clone_repository, pull_latest_changes, post_issue_comment, and fetch_issue_comments) that interact with the Github repo may call that new function to get an authenticated `Github` object.
    4. With this change, Project object may be constructed in an offline fashion for externally cloned repository.

2. **Agent operates on the latest snapshot of the repository**. However, for evaluation purposes the requirement is different. we need the agent to operate on a specific commit hash.
    1. Add a function to Project that allows reseting the repo state to a specified commit hash or by default: the HEAD
    2. Semantic understanding update method in the Project starts by pulling the latest changes in the repo. This is good for live agent but not for evaluation. To facilitate evaluation, let's add a new method to `vector_store_utils`: `create_vector_store(source_dir: str, uri: str, embeddings: Embeddings, commit_hash: str=None) -> VectorStore`. This should create a vector_store at the specified uri, by embedding all the file contents in the source_dir, it should use the relative file path as ids, as well add it as `metadata.filepath`. It should also keep track of uri(s) it created where commit_hash was available, and if for a commit has vector store was previously created as a uri, it should just load and return it (instead of fresh creating the vector store)

3. **Core processor doesn't have a method to drive evaluation for a task instance**.
    1. Let's add a new method to `listener_core.py`: `evaluate(repo_full_name: str, instance_id: str, problem_statement: str, commit_hash: str)`. The method should:
        1. create a project instance.
        2. reset to project repo to commit_hash
        3. create a vector store with source_folder for the commit_hash using the new method we introduce above in `vector_store_utils`.
        4. Create a semantic_vector_search localizer with this vector_store
        5. localize
        6. suggest changes
        7. dump change suggestions to a file
        8. reset project repo back to HEAD
    2. For storing vector stores and change suggestions towards evaluation, 
        1. let's create a folder in project metadata named `evaluation`
        2. For each evaluation instance_id, we create a folder in that named `<instance_id>`
        3. vector_store for the instance_id, and for a specific source type should be named `<vector-type>_vector_store.db`, e.g., for source code embeddings that should be `code_vector_store.db`
        4. change suggestions should be dumped in a file named `change_suggestions.md` in the `<instance_id>` folder