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

# Show the directory structure for debugging
RUN find /app -type f | sort

# Build wheel
RUN pip wheel --no-cache-dir --wheel-dir=/app/wheels -e .

# Show what was built
RUN ls -la /app/wheels/

# Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy wheels from build stage
COPY --from=build /app/wheels /app/wheels

# Install the wheels with verbose output
RUN pip install --no-index --find-links=/app/wheels/ mcp-prompt-manager -v && \
    rm -rf /app/wheels

# Create data directory for persistence
RUN mkdir -p /data

# Create a non-root user
RUN useradd -m mcp && \
    chown -R mcp:mcp /app /data

# Copy in specific script files for direct execution
COPY --from=build /app/src/mcp_prompt_manager/prompt_manager_server.py /app/
COPY --from=build /app/src/mcp_prompt_manager/__init__.py /app/

# Switch to non-root user
USER mcp

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    MCP_PROMPT_MANAGER_PERSISTENCE=true \
    MCP_PROMPT_MANAGER_PERSISTENCE_FILE=/data/templates.json \
    PYTHONPATH=/app

# Volume for persistent template storage
VOLUME /data

# IMPORTANT: Run prompt_manager_server.py directly
ENTRYPOINT ["python", "-c", "from prompt_manager_server import main; main()"]