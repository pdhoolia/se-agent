Current implementation uses a system wide default for vector type.
Vector type is intended to represent the artifact that we are embedding (or vectorizing).
Different vector type documents are added to different collections named after the vector type.
Default vector type is intended to govern the collection that will be used for semantic search while localizing.
At the moment, we only index semantic summaries.
Our research reveals that some embedding models (e.g., `OpenAIEmbeddings`) are really good in directly representing code semantics. I.e., directly embedding the code is more effective than embedding a semantic summary document generated from code.

This proposal intends to enable the following:
1. While updating code understanding, also add direct code content to the vector store. This should be added to the `VectorType.CODE` related collection.
2. Add a new project level configuration, which governs the vector collection that will be used at runtime to localize the issue.