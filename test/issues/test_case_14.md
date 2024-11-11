I see the following in error logs.

```
Added project 'pdhoolia/se-agent-test-repo' to projects list.
[INFO] Cloning repository 'pdhoolia/se-agent-test-repo'...
[INFO] Using local repository folder: '/Users/pdhoolia/projects-store/pdhoolia/se-agent-test-repo/repo'
[INFO] Cloning repository into '/Users/pdhoolia/projects-store/pdhoolia/se-agent-test-repo/repo'...
[INFO] Repository cloned successfully into '/Users/pdhoolia/projects-store/pdhoolia/se-agent-test-repo/repo'
[INFO] Updating codebase understanding incrementally...
[INFO] Pulling latest changes from main branch...
[INFO] Latest changes pulled from main branch.
[INFO] File is empty, no summary generated for file: package2/__init__.py
[ERROR] Error summarizing file 'package2/__init__.py'
Traceback (most recent call last):
  File "/Users/pdhoolia/fun/se-agent/se_agent/project.py", line 166, in update_codebase_understanding
    self.save_checkpoint()
  File "/Users/pdhoolia/fun/se-agent/se_agent/project.py", line 75, in save_checkpoint
    with open(self.checkpoint_file, 'w') as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/Users/pdhoolia/projects-store/pdhoolia/se-agent-test-repo/metadata/checkpoint.json'
[INFO] Updated semantic summary for file: package2/file3.py
[INFO] File is empty, no summary generated for file: package2/subpackage/__init__.py
```