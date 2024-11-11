Earlier we proposed to add a cache to store package details documents as follows

> On onboarding or while handling code changes, our agent generates semantic understanding of code files, and also generates package level summaries. While generating package level summaries, it generates a single detailed document for all the files within the package, however, it doesn't store that document anywhere. So when it processes issues, or issue comments, it generates the package details document again for the packages that the localizer localizes to.
>
> Let's add a cache to store these package details documents.
>
> - Cache should be managed by the project.
> - The cache should be a simple key-value store with the package name as the key, and the package details document as the value.
> - It should be populated before generating a package summary.
> - At the moment a file system based implementation of the cache interface may be sufficient, and it may be stored in the metadata folder.

Let's enhance this to store some additional metadata about the package as well. Specifically, let's store the number of tokens in the package details.

At the moment, we have a top-n packages limit in the localizer. This is governed by an environment variable, which is further overridable via a project configuration. We want to make this limit dynamic as follows:

1. Let's enhance model configuration to add (for each provider) a list of models. For each model add a name, and context_limit fields.
2. Model configuration should support a method to get the context limit for a given task.
3. For file level localization, the localizer should:
   - get the context limit
   - compute the total number of token in the prompt template (without the package details)
   - for each relevant package, get the number of tokens in the package details
   - now keep adding the package details until the next package would make the prompt exceed the context limit

