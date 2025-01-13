# Deploying the agent as a lambda function with docker container images

## Build docker image for lambda deployment

```bash
DOCKER_BUILDKIT=0 docker build --platform linux/arm64 -t se-agent:v1 .
```

DOCKER_BUILDKIT=0 is added to build legacy images. Without this the final step of `create-function` seems to fail with error:
> An error occurred (InvalidParameterValueException) when calling the CreateFunction operation: The image manifest or layer media type for the source image 533266957858.dkr.ecr.us-east-1.amazonaws.com/se-agent:latest is not supported.

## Test the image locally

### Run a container with the image

```bash
docker run --platform linux/arm64 \
    -e PROJECTS_STORE=/projects-store \
    -v /Users/pdhoolia/projects-store:/projects-store \
    -p 9000:8080 se-agent:v1
```

### Test the container

```bash
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
    -H "Content-Type: application/json" \
    --data @lambda_test_event.json
```

## Deploy the image to AWS ECR

1. Run the [get-login-password](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/ecr/get-login-password.html) command to authenticate the Docker CLI to your Amazon ECR registry.
    - Set the --region value to the AWS Region where you want to create the Amazon ECR repository.
    - Replace the AWS account ID with your AWS account ID.
    
    ```bash
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 533266957858.dkr.ecr.us-east-1.amazonaws.com
    ```

2. Create a repository in Amazon ECR using the [create-repository](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/ecr/create-repository.html) command.

    ```bash
    aws ecr create-repository --repository-name se-agent --region us-east-1 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
    ```

    > Note: The Amazon ECR repository must be in the same AWS Region as the Lambda function.

    If successful, you see a response like this:

    ```json
    {
        "repository": {
            "repositoryArn": "arn:aws:ecr:us-east-1:533266957858:repository/se-agent",
            "registryId": "533266957858",
            "repositoryName": "se-agent",
            "repositoryUri": "533266957858.dkr.ecr.us-east-1.amazonaws.com/se-agent",
            "createdAt": "2024-11-05T15:32:46.014000+05:30",
            "imageTagMutability": "MUTABLE",
            "imageScanningConfiguration": {
                "scanOnPush": true
            },
            "encryptionConfiguration": {
                "encryptionType": "AES256"
            }
        }
    }
    ```
    
3. Copy the repositoryUri from the output in the previous step.

4. Run the [docker tag](https://docs.docker.com/engine/reference/commandline/tag/) command to tag your local image into your Amazon ECR repository as the latest version. In this command:
    - `se-agent:v1` is the name and tag of the Docker image. This is the image name and tag that we specified in the docker build command.
    - Replace <ECRrepositoryUri> with the repositoryUri that you copied. Make sure to include :latest at the end of the URI.

    ```bash
    docker tag se-agent:v1 533266957858.dkr.ecr.us-east-1.amazonaws.com/se-agent:latest
    ```

5. Run the [docker push](https://docs.docker.com/engine/reference/commandline/push/) command to deploy the local image to the Amazon ECR repository. Make sure to include :latest at the end of the repository URI.

    ```bash
    docker push 533266957858.dkr.ecr.us-east-1.amazonaws.com/se-agent:latest
    ```

6. [Create an execution role](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html#permissions-executionrole-api) for the function, if you don't already have one. You need the Amazon Resource Name (ARN) of the role in the next step.

7. Create or Identify Your Elastic File System Access Point

   ```bash
   aws efs create-access-point \
        --file-system-id fs-0d930570b7fe7c6fe \
        --posix-user Uid=0,Gid=0 \
        --root-directory "Path=/, CreationInfo={OwnerUid=0,OwnerGid=0,Permissions=755}"
   ```

8. Create the Lambda function. For ImageUri, specify the repository URI from earlier. Make sure to include :latest at the end of the URI.

    ```bash
    aws lambda create-function \
        --function-name se-agent \
        --package-type Image \
        --code ImageUri=533266957858.dkr.ecr.us-east-1.amazonaws.com/se-agent:latest \
        --role arn:aws:iam::533266957858:role/lambda-ex \
        --architectures arm64 \
        --file-system-configs Arn=arn:aws:elasticfilesystem:us-east-1:533266957858:access-point/fsap-0aad1009b828e4f2a,LocalMountPath=/mnt/efs \
        --vpc-config SubnetIds=subnet-02a6fbef9764ca9b3,subnet-09c99b46878e96ecc,subnet-0ec0be1eb10182a9e,subnet-0dd6af6346cb9d27d,subnet-037537a2df0f3aaf8,SecurityGroupIds=sg-0ed499b48caf219d9
    ```

9. Add a Function URL

10. Test the function

    ```bash
    curl -X POST "https://tactdzce7uhbesuruedr5tktwi0bfmih.lambda-url.us-east-1.on.aws/onboard" \
        -H "Content-Type: application/json" \
        --data @lambda_onboard_event.json
    ```

## Changing configurations etc.

### Change timeout?

```bash
aws lambda update-function-configuration \
    --function-name se-agent \
    --timeout 600
```