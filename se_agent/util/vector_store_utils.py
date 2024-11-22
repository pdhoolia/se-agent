from enum import Enum
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_milvus import Milvus


class VectorType(Enum):
    CODE = "code"
    SEMANTIC_SUMMARY = "semantic_summary"

DEFAULT_VECTOR_TYPE = VectorType.SEMANTIC_SUMMARY.value

def get_or_create_vector_store(embeddings: Embeddings, uri: str, collection_name: str) -> VectorStore:
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={"uri": uri}
    )
    return vector_store
