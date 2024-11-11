Let's add a new route to onboard a new project: `/onboard`. This should support a POST/PUT with a json corresponding to the `ProjectInfo` structure. It should add the new project and then trigger its onboarding. We should use POST for new projects and PUT for forcing updates for existing projects.

We should add this support to all the channels of hosting the agent that we support.

Also, let's create a github page that can be used as the UI to initiate onboarding. This page should have a form that can be filled in with the project details and then submitted to the agent. The agent should then onboard the project and respond with success or failure status. Let's use Carbon Design System for creating this page.