Current implementation of semantic vector strategy seems to have an overly complex design.

Project seems to maintain an instance of semantic vector localization strategy, which seems to manage various semantic vector collections for the project.
While handling issue events, this instance of localization strategy is fetched and used.
This seems to be the wrong dependency structure without the right kind of separation of concerns.

Following code refactoring is proposed:
1. Separate the vector store management concern from localization strategy. Let the project be responsible for getting or creating a vector store. 
2. Rather than creating / loading the vector store as a member of the project during its construction, let's get or create it on demand. this will minimize the high memory requirement periods. Further only load the collection that is needed
3. Let SemanticVectorSearchLocalizer be constructed by injecting the vector store into it. Let it only have the localize method.
4. The methods to add / delete documents from the vector store are already available on langchain's VectorStore abstraction that we use. There is no point in replicating them once again. While adding documents to vector store (during semantic understanding) let's directly use the VectorStore's add_documents method.