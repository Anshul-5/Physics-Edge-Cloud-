FROM python:3.11-slim@sha256:9c900dea9e8fb7e16277c179b555cc72d29a352dbc33cff48ad5a0412fd5bfc7

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Use a higher timeout for large packages like torch
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY . .

# By default, just run tests to verify the engine works
CMD ["pytest", "."]
