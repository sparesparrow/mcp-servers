FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directory for custom themes
RUN mkdir -p /root/.mermaid_themes

# Default environment variables
ENV PYTHONUNBUFFERED=1
ENV CACHE_TTL=3600
ENV CALLS_PER_MINUTE=25
ENV DEFAULT_THEME=default
ENV CUSTOM_THEMES_PATH=/root/.mermaid_themes.json
ENV SERVER_TYPE=standard

# Start the server when the container launches
CMD ["sh", "-c", "if [ \"$SERVER_TYPE\" = \"orchestrator\" ]; then python -m src.mermaid.mermaid_orchestrator; else python -m src.mermaid.mermaid_server; fi"]
