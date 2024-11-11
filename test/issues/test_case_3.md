Our software engineering agent receives new issue events from GitHub via a web-hook, localizes them via hierarchical documentation it had generated previously while onboarding, to specific packages and files, and then makes recommendations about code changes that may help fix, or enhance the code in accordance with the issue details.

We now want to enhance this agent to handle issue comments as well.

The Agent only processes new issue events at the moment. Let's add the ability to process issue comment events as well. Of course we want the issue comment event also to go thru the same processing pipeline.
This will require a few changes. E.g.,

1. GitHub listener will need to be updated to listen for issue comment events. However, we should not trigger processing if the new comment is made by the SE Agent itself. Recognizing SE Agent comment may be tricky. For testing purposes we use the same user to raise the issue, as well as for programmatic posting of SE Agent's suggestion. Therefore, while posting agents suggestions as a comment we should add a special string to it, something like `<!-- SE Agent -->`.

2. With this feature, there we may be processing a conversation thread made up of comments on the issue. E.g., user may post a new issue, then SE agent may reply to it with some suggestions, then user may post something to refine that etc. We need to make sure that the SE agent passes all these messages to the LLM while localizing and generating change suggestions. This will require changes to the way we build the prompt for LLM and how we call it. Here's something to consider:

   - issue analysis may check the issue details to see if there are any comments.
   - If there are comments, it should add a `comments` field to the analysis result, which is a list of all those comments.
   - Each comment should be recorded as `{role: '<role>', content: '<content>'}`. Role being either `user` or `agent`, and the `content` being the issue body, or the comment text.
   - The current functions that generate the various prompts (for localization and suggestions etc.) should return a `Prompt` object with a list of messages instead of a single string. The messages should include the `system` role message, as well as the user and agent messages as discussed above. This is to make it convenient to pass the messages to the LLM model.
   
3. The functions that drive the llm calls (for localization and suggestions etc.) should be refactored to take the structured prompt as input.

Also consider the following:

- Since we expect to process new issues and new comments via the same pipeline we should enforce the DRY principle to avoid code duplication.

- Whie we should prevent the agent's comments from triggering any new comment processing, we should use the agent's comment as a part of the conversation to refine previous suggestions, rather than trying to answer th whole thing fresh on every use comment.

- Also like we discussed earlier, we should use the presence  of `<!-- SE agent -->` to decide the role of the comment, rather than the user (since for testing, we are using the same user for raising the issue and his github token to post as Agent as well.)