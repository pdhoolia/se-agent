At the moment our agent automatically responds to every issue that is raised on the project, as well as to every comment that is made on the issue. This may be useful in many cases, but there may be cases where developers may consider this too intrusive or cluttering the issue. Therefore, we want to allow developer to label any issue as "off limit" for the agent.

Agent should listen to events related to labeling an issue. If an issue is labeled with a specific label, e.g., "off-limit", then the agent should
   - not respond to any comments on that issue from that point on (until that label is removed from the issue)
   - hide all the comments that may have been made by the agent on that issue

Note: we should use the convention that we are currently using for the agent to spot its own comments.