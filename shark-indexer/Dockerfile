FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y gcc python3-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy source code and configuration files
COPY . .

# Install package and dependencies
RUN pip install requests>=2.31.0
RUN pip install -e .

# Install aioredis specifically to fix dependency issues
RUN pip install aioredis==2.0.1

# Create and switch to non-root user
RUN useradd -m indexer
USER indexer

CMD ["python", "-m", "shark_indexer"] 