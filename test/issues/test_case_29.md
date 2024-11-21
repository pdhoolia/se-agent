ATM our software engineering agent builds a semantic understanding for each code file in the repository, and stores it as metadata. It then uses those semantic summaries to localize any issues raised on the repository.
Earlier we were using a hierarchical localization strategy. In that strategy the agent created an inline context for the LLM by aggregating semantic summary files, and then made a completion API call to generate localization suggestions.

We have recently added support for a new localization strategy based on semantic vector search. In this strategy, in addition to generating semantic summaries for code files and storing them in metadata, the agent also wants to create a vector store that indexes embeddings for those semantic summaries.

Before releasing the new localization strategy into production, we need to migrate the existing projects to create the vector stores required in support of this strategy. I am assuming we'll need to write a migration script that will list all projects, and for each project populate the vector store with the semantic summaries of all code files in the metadata.