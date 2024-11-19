ATM: a single strategy of `localization` has been implemented.
We need to refactor to support multiple strategies. For instance, it should be possible to use a semantic vector search to localize issue to relevant instead of the hierarchical package localization followed by file localization as currently implemented.

For this refactoring following changes are proposed:

1. **An abstract `LocalizationStrategy` interface**

    ```python
    class LocalizationStrategy(ABC):
        @abstractmethod
        def localize(self, issue: Dict[str, str], top_n: int) -> List[str]:
            """
            Localizes the issue to a set of relevant packages and files.
    
            Args:
                issue (Dict[str, str]): A dictionary containing issue details with at least:
                    - `title` (str): The title of the issue.
                    - `description` (str): The detailed description of the issue.
                top_n (int): The maximum number of localization results to return.
    
            Returns:
                List[str]: A list of relevant filepaths (relative from repo root)
            """
            pass
    ```

2. **A `HierarchicalLocalizationStrategy` class** extending the `LocalizationStrategy` and wrapping around the current localization implementation.

3. Let's ignore the current `localize_issue` altogether. Let's pick the strategy in the caller that is processing the issue events, and directly invoke the newly created HierarchicalLocalizationStrategy.

4. Since we are changing the interface a little from the previous `localize_issue`, i.e., instead of `FileLocalizationSuggestions` we are now returning: `List[str]` where each `str` is a relative file path in the repository, let's also adjust the follow on change suggester and file fetching logic to be sensitized to that