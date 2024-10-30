Title: Avoid user annoyance

Description:
There may be cases where other users think that our agent's responses to the issue, or issue comments are adding clutter. In such cases we want the agent to support a pattern where if users put an agreed upon label on the issue, e.g., "Off-Agent", then the agent should hide all the comments that may have been made by the agent on that issue, and should not attempt to respond to future comments on that issue, unless user(s) once again remove the "Off-Agent" label. For this:

Our github events listener will need to additionally listen to new events related to label addition on an issue.
It should process that event by "hiding" all the issue comment made by the se-agent. Note: we should use convention that we are using currently to spot agent's own comments for this.
We should modify the new event or issue comment processing to also check for "Off-Agent" label on the issue. If the issue is carrying that label, then we should not process those events as well.