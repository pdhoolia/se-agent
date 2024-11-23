"""Module for localizing issues to relevant code files using semantic vector search."""

from typing import Dict, List
from langchain_core.vectorstores import VectorStore

from se_agent.localize.localization_strategy import LocalizationStrategy
from se_agent.util.vector_store_utils import VectorType

# Default vector type for the vector store
DEFAULT_VECTOR_TYPE = VectorType.SEMANTIC_SUMMARY.value

class SemanticVectorSearchLocalizer(LocalizationStrategy):
    """Implements a semantic vector search-based localization strategy.

    Attributes:
        vector_store (VectorStore): The vector store used for similarity-based searches.
    """
    def __init__(self, vector_store: VectorStore):
        """Initializes the SemanticVectorSearchLocalizer with a vector store.

        Args:
            vector_store (VectorStore): The vector store containing embeddings and metadata for similarity search.
        """
        self.vector_store = vector_store

    def localize(self, issue: Dict[str, str], top_n: int) -> List[str]:
        """Localizes an issue to the most relevant code files.

        Uses the issue's title and description to perform a similarity search in the vector store.

        Args:
            issue (Dict[str, str]): A dictionary containing the issue's title and description.
            top_n (int): The maximum number of relevant files to return.

        Returns:
            List[str]: A list of file paths corresponding to the most relevant code files.
        """
        # Construct the query by combining the issue title and description
        query = f"{issue['title']}: {issue['description']}"
        # Perform a similarity search in the vector store
        results = self.vector_store.similarity_search(query, k=top_n)
        # Extract and return the file paths from the search results
        return [result.metadata['filepath'] for result in results]