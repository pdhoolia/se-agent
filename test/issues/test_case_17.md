We currently support multiple events. E.g., 
- onboard event on `/onboard` route
- and various github events on `/webhook` route

The new issue, and issue comment events on `/webhook` route are synchronous events, and the agent processes them in realtime.

The `/onboard` route is a potentially long running event (with a client actually waiting on it). It onboards the agent onto the requested GitHub repository, which requires:

1. cloning the repository
2. generating semantic understanding for each code file in the repository, or building a vector index for the repository

This should be considered for asyncronous processing pattern, as depending on the size of repository, this may take significant amount of time (e.g. for a repository with 1000 code files, it may take 30+ mins to onboard). The time may be way beyond even the max timeout limit for a lambda function.

We need to refactor how we serve such long running processes. We need something on the following pattern:
- For a POST/PUT on `/onboard` queue up the request to be processed in the background, and return immediately with `In progress` status
- On GET on `/onboard` return the current status of onboarding, which may be `In progress`, or `Error`, or `Complete`, with an according `message`

This may need to be refactored for both the lambda, and flask based serving.
