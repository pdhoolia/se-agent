Our localizer uses a hierarchical approach to find the files relevant for an issue.
1. First, it aggregates all semantic packages summaries, and asks an LLM to find packages relevant to the issue
2. Then, it aggregates the file level semantic summaries of top-k relevant packages, and asks the LLM to find files relevant to the issue. This strategy has few challenges:

    - The LLM is being used twice (sequentially) in the process, which has latency as well as cost implications.
    - For issues cutting across multiple packages, the localizer may be forced to use only the top-k packages due to token limits. We may miss out on relevant files in other packages.

The code level semantic summaries, and package level semantic summaries are generated while onboarding the project.

Let's implement an alternate strategy based on Retrieval Augmented Generation as well.

- Let's associate a vector index (we can use a local vector store for the project). This vector index may be created at the time of initial project onboarding, in the metadata folder (if it doesn't already exist).

- We will use Milvus with langchaing based adaptations.

- Code file semantic summaries that are already being generated during the onboarding process, should be added as a document to this vector index as well. File name and fully qualified package affiliation should be added as metadata to the documents being indexed.

- We'll use Langchain based adaptation in both the the process of creating the vector index, as well as its use during localization.

- An alternative localizer should be implemented with similar input and output expectation as the current localizer. This localizer should return `FileLocalizationSuggestions`.

- Current LLM interfacing should be enhanced to provide the LLM components (e.g., embedding models) necessary. We can add embedding as yet another task to our model congifurations.