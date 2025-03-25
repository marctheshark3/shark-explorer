FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY setup.py .
COPY src ./src

# Set environment variable to disable Prometheus multiprocessing
ENV PROMETHEUS_MULTIPROC_DIR=""

RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8082

# Run the application
CMD ["uvicorn", "shark_api.main:app", "--host", "0.0.0.0", "--port", "8082"] 