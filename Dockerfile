# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./src ./src
COPY ./configs ./configs    


COPY ./lambda_handler ./lambda_handler


# Set entrypoint
ENTRYPOINT ["python"]



