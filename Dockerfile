# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.9

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code to the Lambda task root
COPY ./src ${LAMBDA_TASK_ROOT}/src
COPY ./configs ${LAMBDA_TASK_ROOT}/configs
COPY ./lambda_handler ${LAMBDA_TASK_ROOT}/lambda_handler

# Create __init__.py files to make Python packages
RUN touch ${LAMBDA_TASK_ROOT}/lambda_handler/__init__.py
RUN touch ${LAMBDA_TASK_ROOT}/lambda_handler/optimizer/__init__.py
RUN touch ${LAMBDA_TASK_ROOT}/src/__init__.py

# Set the Lambda handler
CMD ["lambda_handler.optimizer.handler.lambda_handler"]