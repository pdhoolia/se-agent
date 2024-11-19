from abc import ABC, abstractmethod
from typing import Dict, List

class LocalizationStrategy(ABC):
    @abstractmethod
    def localize(self, issue: Dict[str, str], top_n: int) -> List[str]:
        """
        Localizes the issue to a set of files.

        Args:
            issue (Dict[str, str]): A dictionary containing issue details with at least:
                - `title` (str): The title of the issue.
                - `description` (str): The detailed description of the issue.
            top_n (int): The maximum number of localization results to return.

        Returns:
            List[str]: A list of relevant filepaths (relative from repo root)
        """
        pass