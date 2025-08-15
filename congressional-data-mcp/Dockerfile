# Congressional Data MCP Server Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY pyproject.toml .
COPY README.md .

# Create directories for configs and logs
RUN mkdir -p /app/config /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_SERVER_NAME=congressional-data-mcp

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Expose port for potential future HTTP interface
EXPOSE 8080

# Run the MCP server
CMD ["python", "server.py"]
