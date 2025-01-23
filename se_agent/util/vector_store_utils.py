"""Utilities for managing vector stores using Milvus and embeddings."""

import os
import logging
from enum import Enum
from typing import List
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_milvus import Milvus

logger = logging.getLogger("se-agent")


class VectorType(Enum):
    """Enumeration of vector types available."""

    CODE = "code"
    SEMANTIC_SUMMARY = "semantic_summary"


DEFAULT_VECTOR_TYPE = VectorType.SEMANTIC_SUMMARY.value


def get_vector_store(embeddings: Embeddings, uri: str) -> VectorStore:
    """Load a Milvus vector store from the specified uri.

    Args:
        embeddings (Embeddings): The embedding function to use.
        uri (str): The URI for connecting to Milvus.

    Returns:
        VectorStore: The Milvus vector store instance.
    """

    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"uri": uri},
        index_params=None if uri.startswith("http") else {"index_type": "FLAT", "metric_type": "L2", "params": {}}
    )
    return vector_store

def create_or_update_vector_store(source_dir: str, uri: str, embeddings: Embeddings, path_prefix: str = "") -> VectorStore:
    """Creates a vector store for files in source_dir using embeddings and saves at the specified URI.

    Args:
        source_dir (str): Directory containing source files to embed.
        uri (str): URI for storing/loading the vector store.
        embeddings (Embeddings): Embedding function to use.
        path_prefix (str): Prefix for filepaths metadata/IDs.

    Returns:
        VectorStore: The vector store instance.
    """
    contents, filepaths = [], []
    for root, _, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'r') as f:
                contents.append(f.read())
            filepaths.append(os.path.join(path_prefix, os.path.relpath(file_path, source_dir)))

    return add_documents(contents, filepaths, uri, embeddings)

def add_documents(contents: List[str], filepaths: List[str], uri: str, embeddings: Embeddings) -> VectorStore:
    """Adds documents to a vector store, creating it if it does not exist.

    Args:
        contents (List[str]): The content of the documents to embed.
        filepaths (List[str]): The file paths corresponding to the contents.
        uri (str): The URI for storing/loading the vector store.
        embeddings (Embeddings): The embedding function to use.

    Returns:
        VectorStore: The vector store instance.
    """
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"uri": uri},
        index_params=None if uri.startswith("http") else {"index_type": "FLAT", "metric_type": "L2", "params": {}}
    )

    if filepaths:
        vector_store.add_documents(
            documents=[
                Document(page_content=content, metadata={"filepath": filepath})
                for content, filepath in zip(contents, filepaths)
            ],
            ids=filepaths,
        )
        logger.info(f"Added {len(filepaths)} documents to the vector store.")

    return vector_store
