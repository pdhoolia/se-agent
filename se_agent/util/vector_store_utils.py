"""Utilities for managing vector stores using Milvus and embeddings."""

from enum import Enum
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_milvus import Milvus


class VectorType(Enum):
    """Enumeration of vector types available."""

    CODE = "code"
    SEMANTIC_SUMMARY = "semantic_summary"


DEFAULT_VECTOR_TYPE = VectorType.SEMANTIC_SUMMARY.value


def get_or_create_vector_store(embeddings: Embeddings, uri: str, collection_name: str) -> VectorStore:
    """Gets or creates a Milvus vector store.

    Args:
        embeddings (Embeddings): The embedding function to use.
        uri (str): The URI for connecting to Milvus.
        collection_name (str): The name of the collection in Milvus.

    Returns:
        VectorStore: The Milvus vector store instance.
    """
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={"uri": uri}
    )
    return vector_store