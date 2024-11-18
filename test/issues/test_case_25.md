Let's refactor the localizer.

ATM a hierarchical localization strategy has been implemented. This makes 2 calls to the LLM. First call uses package summaries in the context to localize the issue to relevant packages. Second call uses the package details for the relevant packages to localize the issue to relevant files.

This refactor should introduce an abstract localization strategy interface with a localize method that takes issue_details, and a top_n count as input, returning a list of localization suggestions with each suggestion having attributes such as: package, file, confidence, and reason. Each localization strategy should have a name.
It should then add a class extending that interface to execute the currently implemented strategy. It should call it hierarchical localization.

In addition we should also add a configuration: localization_strategy in `.env`. Its value should map to the name of the strategy to be used for localization.

In addition we want to introduce a new semantic vector search strategy. This will use `Milvus` as the vector database and an embedding model to vectorize repository artifacts (or semantic summaries generated from the repository artifacts). In support of this strategy, at the time of updating semantic code understanding, we should first create a Milvus vector store (if it doesn't exist), we should then add a Milvus collection for the project (if it doesn't already exist). We should then add / replace the semantic summary document for the code file into the Milvus collection.