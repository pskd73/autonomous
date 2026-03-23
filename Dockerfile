FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY agent/requirements.txt /app/agent/requirements.txt
RUN pip install --no-cache-dir -r /app/agent/requirements.txt

# Copy application
COPY agent /app/agent
COPY scripts /app/scripts
COPY test_client.py /app/test_client.py

RUN chmod +x /app/scripts/start.sh

EXPOSE 8000

ENV PYTHONPATH=/app/agent
ENV PORT=8000
ENV WORKSPACE_PATH=/workspace

# Run single websocket server
CMD ["/app/scripts/start.sh"]