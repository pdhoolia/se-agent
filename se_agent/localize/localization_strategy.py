"""Abstract base classes and enums for localization strategies."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List


class LocalizationStrategy(ABC):
    """Abstract base class for implementing localization strategies."""

    @abstractmethod
    def localize(self, issue: Dict[str, str], top_n: int) -> List[str]:
        """Localizes the issue to a set of files.

        Args:
            issue (Dict[str, str]): A dictionary containing issue details with at least:
                - `title` (str): The title of the issue.
                - `description` (str): The detailed description of the issue.
            top_n (int): The maximum number of localization results to return.

        Returns:
            List[str]: A list of relevant file paths (relative from repo root).
        """
        pass


class LocalizationStrategyType(Enum):
    """Enumeration of localization strategy types."""

    HIERARCHICAL = "hierarchical"  # Localization based on hierarchical project structure
    SEMANTIC_VECTOR_SEARCH = "semantic_vector_search"  # Localization using semantic vector search