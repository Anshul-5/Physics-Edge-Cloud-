FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

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
