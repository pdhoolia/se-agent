from typing import Dict, List
from langchain_core.vectorstores import VectorStore

from se_agent.localize.localization_strategy import LocalizationStrategy
from se_agent.util.vector_store_utils import VectorType

DEFAULT_VECTOR_TYPE = VectorType.SEMANTIC_SUMMARY.value

class SemanticVectorSearchLocalizer(LocalizationStrategy):
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def localize(self, issue: Dict[str, str], top_n: int) -> List[str]:
        query = f"{issue['title']}: {issue['description']}"
        results = self.vector_store.similarity_search(query, k=top_n)
        return [result.metadata['filepath'] for result in results]