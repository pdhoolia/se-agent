Title: Structured output from semantic summarization generation task

Description:
We use large language models to generate a semantic summary in a specific markdown format for a code file, or a higher order summary at the level of packages. Some of the models tend to add some prefix and suffix to the markdown in their. E.g.,
- Here's what i have done ...
- Let me know if this is what you wanted ...

Let's go with a structured output parsing approach similar to what is used in the `localizer.py`, and put together the markdown file in the wrapper code in project.py before we write the files out in the metadata.