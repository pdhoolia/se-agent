At the moment our agent automatically responds to every issue that is raised on the project, as well as to every comment that is made on the issue. The job of the agent here is to help resolve issues and not really to just engage in a conversation. There are many scenarios where no response may be desired from the agent, or just an emoji reaction may be sufficient to ackowledge a comment. E.g.,

- If a comment is suggesting that the proposed solution works great, or is just a thank you note, then a thumbs-up emoji as a reaction to that comment may be sufficient.

- If the conversation on the issue as a whole (specifically some comments from other users) is suggesting that the agent should hold off on making any suggestions or response for now, then a thumbs-down emoji as a reaction to such a comment may be sufficient, and the agent should not respond to any further comments on that issue, unless the conversation starts to suggest otherwise.


So, we want to enhance the agent as follows:

1. After issue analysis, the core processing logic may add a guard rail step to decide from the one of te following courses of action:
    - continue processing: i.e., localize, and generate suggestions as usual
    - acknowledge with a thumbs-up emoji on a comment
    - ignore processing: i.e., no need to respond, or react with an emoji on a comment

2. Such decision making may be implemented using a new LLM task `response_decision`. A decision classification prompt may be generated for this task, using the issue conversation, along with classes of decisions discussed above.

3. Enhancements may be needed to add emoji reactions to comments (using GitHub API).