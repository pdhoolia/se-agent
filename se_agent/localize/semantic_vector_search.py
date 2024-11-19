from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_milvus import Milvus
from typing import Dict, List, Tuple

from se_agent.localize.localization_strategy import LocalizationStrategy, VectorType

DEFAULT_VECTOR_TYPE = VectorType.SEMANTIC_SUMMARY.value

class SemanticVectorSearchLocalization(LocalizationStrategy):
    def __init__(self, uri: str, embeddings: Embeddings, collection_name: str=DEFAULT_VECTOR_TYPE):
        self.uri = uri
        self.embeddings = embeddings
        self.vector_stores: Dict[str, Milvus] = {}
        # Initialize the default collection
        self._get_vector_store(collection_name)
    
    def _get_vector_store(self, collection_name: str) -> Milvus:
        if collection_name not in self.vector_stores:
            # Create a new Milvus vector store for the collection_name
            vector_store = Milvus(
                embedding_function=self.embeddings,
                collection_name=collection_name,
                connection_args={"uri": self.uri}
            )
            self.vector_stores[collection_name] = vector_store
        return self.vector_stores[collection_name]
    
    def add_documents(self, files: List[Tuple[str, str]], collection_name: str=DEFAULT_VECTOR_TYPE):
        vector_store = self._get_vector_store(collection_name)
        ids = [filepath for filepath, _ in files]
        documents = [
            Document(page_content=content, metadata={"filepath": filepath})
            for filepath, content in files
        ]
        vector_store.add_documents(documents, ids=ids)
    
    def add_document(self, filepath: str, content: str, collection_name: str=DEFAULT_VECTOR_TYPE):
        vector_store = self._get_vector_store(collection_name)
        vector_store.add_documents(
            documents=[Document(page_content=content, metadata={"filepath": filepath})], 
            ids=[filepath]
        )
    
    def delete_documents(self, filepaths: List[str], collection_name: str=DEFAULT_VECTOR_TYPE):
        if collection_name not in self.vector_stores:
            raise ValueError(f"Collection {collection_name} does not exist.")
        vector_store = self.vector_stores[collection_name]
        vector_store.delete(ids=filepaths)
    
    def localize(self, issue: Dict[str, str], top_n: int, collection_name: str=DEFAULT_VECTOR_TYPE) -> List[str]:
        if collection_name not in self.vector_stores:
            raise ValueError(f"Collection {collection_name} does not exist.")
        vector_store = self.vector_stores[collection_name]
        query = f"{issue['title']}: {issue['description']}"
        results = vector_store.similarity_search(query, k=top_n)
        return [result.metadata['filepath'] for result in results]