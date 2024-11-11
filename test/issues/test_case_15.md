I see the following on console:

```
2024-11-07 22:47:06,660 - se-agent - DEBUG - Projects store: /Users/pdhoolia/projects-store
Added project 'pdhoolia/se-agent-test-repo' to projects list.
2024-11-07 22:47:06,665 - se-agent - ERROR - Error during project onboarding.
Traceback (most recent call last):
  File "/Users/pdhoolia/fun/se-agent/se_agent/listener_core.py", line 48, in onboard_project
    project.onboard()
  File "/Users/pdhoolia/fun/se-agent/se_agent/project.py", line 240, in onboard
    self.clone_repository()
  File "/Users/pdhoolia/fun/se-agent/se_agent/project.py", line 79, in clone_repository
    if os.listdir(self.repo_folder):
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/Users/pdhoolia/projects-store/pdhoolia/se-agent-test-repo/repo'
```