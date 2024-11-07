Title: Allow GitHub-token to be overridable per project

Description: At the moment a github_token is read as a global environment parameter.
We intend for our agent to be onboarded to multiple projects. Different projects may require different github_token(s).
Let's extend our project structure to add github_token as an optional parameter.
When present, its value should be used for authentication.
