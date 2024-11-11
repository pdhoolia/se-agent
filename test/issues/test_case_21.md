In an earlier enhancement we proposed for the agent to recognize, and store domain (project) memories. These memories are generated when users specify some domain nuances which may be useful (in the context of this project in general) for the agent to incorporate in its localization, and change suggestion processes. As a part of that enhancement, agent should store these memories in a memory store using the following schema:

```json
{
    "memory_id": "<memory_id>",
    "issue_id": "<github_issue_id>",
    "comment_id": "<github_comment_id>",
    "memory": "This is a memory text",
    "user_id": "<github_user_id>",
    "created_at": "2021-08-01T12:00:00Z",
    "updated_at": "2021-08-01T12:00:00Z",
    "status": "<new | accepted | rejected | needs_review>"
}
```
We propose that agent offers a new API endpoint to manage these memories. This endpoint should support the following operations:

- `GET /{project_id}/memories`: This should return a list of memories stored by the agent for the project. The response should be a JSON array of memory objects as described above.
- `PUT /{project_id}/memories/{memory_id}`: This should allow an expert to update the status of a memory. The request body should contain a JSON object with the following fields:
    - `memory` (optional): The new memory text. If this is provided, the memory text should be updated to this value. Provided it passes the validation checks (e.g., token length limits).
    - `status`: The new status of the memory. This should be one of `new`, `accepted`, `rejected`, or `needs_review`.
