# Use Python 3.11 slim image
FROM python:3.11-slim

# Prevent debconf and pip warnings during build
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_ROOT_USER_ACTION=ignore
ENV PIP_NO_WARN_SCRIPT_LOCATION=1

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY registry.py .
COPY tools/ tools/

# Copy environment example (users should mount their own .env)
COPY .env .

# Create a non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose HTTP port
EXPOSE 8080

# Set default environment (can be overridden)
ENV MCP_TRANSPORT=http \
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=8080

# Run the server
CMD ["python", "server.py"]
