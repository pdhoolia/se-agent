Title: Refactor lambda function: for long running routes

Description:
So our lambda function currently supports multiple routes, e.g., `/onboard`, and `/webhook`. While the `/webhook` route expects synchronous (realtime) response, the `/onboard ` route may be long running. `/onboard` processing, onboards the agent onto the requested GitHub repository, which requires:

1. cloning the repository
2. generates semantic understanding for each code file in the repository

Depending on the size of repository, this may take significant amount of time, even of the order of 30 mins (if the repository has 1000 code files), which is way beyond even the max timeout limit that may be setup for a lambda function. How should we refactor our lambda function implementation in support of this.

Could we implement it as follows:
- For a route like `/onboard` we support POST/PUT, and now GET well.
- On POST, we fire a background thread of processing but return immediately with an `In progress` status
- On GET, we return the current `status` of onboarding, which may be `In progress`, or `Error`, or `Complete`, with an according `message`

Does this make sense, and is this easy to implement with AWS lambda?