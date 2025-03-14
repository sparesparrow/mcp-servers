# Dockerfile for MCP System Context Server

# Build stage
FROM python:3.11-slim AS build

WORKDIR /app

# Copy only requirements-related files first
COPY setup.py .
COPY pyproject.toml* .
COPY README.md .

# Install build dependencies
RUN pip install --no-cache-dir build wheel setuptools && \
    pip install --no-cache-dir mcp pydantic

# Copy source code
COPY src/ /app/src/

# Build wheel
RUN pip wheel --no-cache-dir --wheel-dir=/app/wheels -e .

# Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy wheels from build stage
COPY --from=build /app/wheels /app/wheels

# Install the wheels
RUN pip install --no-index --find-links=/app/wheels/ mcp-prompt-manager && \
    rm -rf /app/wheels

# Create data directory for persistence
RUN mkdir -p /data

# Create a non-root user
RUN useradd -m mcp && \
    chown -R mcp:mcp /app /data

# Switch to non-root user
USER mcp

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    MCP_PROMPT_MANAGER_PERSISTENCE=true \
    MCP_PROMPT_MANAGER_PERSISTENCE_FILE=/data/templates.json

# Volume for persistent template storage
VOLUME /data

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD pip list | grep mcp-prompt-manager || exit 1

# Run the MCP server using the correct module path
ENTRYPOINT ["python", "-m", "mcp_prompt_manager"] 