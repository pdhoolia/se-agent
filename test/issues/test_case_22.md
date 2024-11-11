On onboarding or while handling code changes, our agent generates semantic understanding of code files, and also generates package level summaries. While generating package level summaries, it generates a single detailed document for all the files within the package, however, it doesn't store that document anywhere. So when it processes issues, or issue comments, it generates the package details document again for the packages that the localizer localizes to.

Let's add a cache to store these package details documents.

- Cache should be managed by the project.
- The cache should be a simple key-value store with the package name as the key, and the package details document as the value.
- It should be populated before generating a package summary.
- At the moment a file system based implementation of the cache interface may be sufficient, and it may be stored in the metadata folder.