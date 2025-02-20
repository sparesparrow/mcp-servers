# Dockerfile for MCP System Context Server

FROM python:3.10-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for remote transport
EXPOSE 8080

# Run the MCP System Context Server
CMD ["python", "src/system-context/mcp_system_context/server.py"] 