FROM public.ecr.aws/lambda/python:3.12

# Install Git (required by gitpython)
RUN dnf update -y && \
    dnf install -y git && \
    dnf clean all

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Copy the se_agent folder
COPY se_agent ${LAMBDA_TASK_ROOT}/se_agent

# Copy .env file
COPY lambda.env ${LAMBDA_TASK_ROOT}/.env

# Copy llm config
COPY llm_config.yaml ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "se_agent.lambda.lambda_function.handler" ]