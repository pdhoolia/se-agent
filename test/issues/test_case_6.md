At the moment we have a lambda function wrapper which is outside the core `se_agent` package.
Does it make sense to move it inside the core package? So it become part of the module itself?
I suggest we create a sub-package - `lambda` inside `se_agent`, and push `lambda_function.py` there.
Our docker container based deployment for the lambda function has the following Dockerfile to build the lambda function image:

```
FROM public.ecr.aws/lambda/python:3.12

# Install Git (required by gitpython)
RUN dnf update -y && \
    dnf install -y git && \
    dnf clean all

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Copy the source code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Copy __init__.py
COPY __init__.py ${LAMBDA_TASK_ROOT}

# Copy .env file
COPY lambda.env ${LAMBDA_TASK_ROOT}/.env

# Copy llm config
COPY llm_config.yaml ${LAMBDA_TASK_ROOT}

# Copy the se_agent folder
COPY se_agent ${LAMBDA_TASK_ROOT}/se_agent

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]
```

We should also change it, if we push `lambda_function.py` into `se_agent.lambda` package?