from typing import Dict, List

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_milvus import Milvus


class VectorStoreManager:
    @classmethod
    def get_vector_store(embeddings: Embeddings, uri: str, collection_name: str) -> VectorStore:
        vector_store = Milvus(
            embedding_function=embeddings,
            collection_name=collection_name,
            connection_args={"uri": uri}
        )
        return vector_store
    
    @classmethod
    def add_documents(vector_store: VectorStore, documents: List[Document], ids: List[str]):
        vector_store.add_documents(documents, ids=ids)

    @classmethod
    def delete_documents(vector_store: VectorStore, ids: List[str]):
        vector_store.delete(ids=ids)
