Title: Add API to onboard new project

Description:
Let's add a new route to onboard a new project: `/onboard`. This should support a POST with a json corresponding to the `ProjectInfo` structure. It should add the new project and then trigger its onboarding.

We should rename our flask server file to just `listener.py` to accommodate this new role.