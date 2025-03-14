# Testing Guide for MCP Servers

This guide covers the testing procedures for the three MCP servers in this repository:
1. SOLID Analyzer
2. Mermaid Generator
3. Code Diagram Orchestrator

## Unit Testing

Each server has its own test suite that can be run independently.

### Running All Tests

```bash
pytest
```

### Running Tests for Specific Servers

```bash
# Test just the SOLID server
pytest tests/test_solid_server.py

# Test just the Mermaid server
pytest tests/test_mermaid_server.py

# Test just the Orchestrator
pytest tests/test_orchestrator.py
```

### Test Coverage

```bash
pytest --cov=src tests/
```

## Integration Testing

Integration tests ensure that the servers can work together properly.

### Testing Orchestrator with Other Servers

1. Start all three servers:
   ```bash
   # Terminal 1
   python -m src.solid.solid_server
   
   # Terminal 2
   python -m src.mermaid.mermaid_server
   
   # Terminal 3
   python -m src.orchestrator.code_diagram_orchestrator
   ```

2. Use a client to send requests to the orchestrator, which will coordinate with the other servers.

### Using Docker Compose for Integration Testing

```bash
export ANTHROPIC_API_KEY="your-api-key"
docker-compose up
```

## Manual Testing

### Mermaid Server

Test each of the Mermaid server tools:

1. **generate_diagram**
   ```json
   {
     "tool": "generate_diagram",
     "params": {
       "query": "Create a flowchart for user registration process"
     }
   }
   ```

2. **analyze_diagram**
   ```json
   {
     "tool": "analyze_diagram",
     "params": {
       "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]"
     }
   }
   ```

3. **modify_diagram**
   ```json
   {
     "tool": "modify_diagram",
     "params": {
       "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]",
       "modification": "Add a decision node after Process"
     }
   }
   ```

4. **validate_diagram**
   ```json
   {
     "tool": "validate_diagram",
     "params": {
       "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]"
     }
   }
   ```

### SOLID Server

Test each of the SOLID server tools:

1. **analyze_code**
   ```json
   {
     "tool": "analyze_code",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)",
       "principles": ["Single Responsibility Principle"]
     }
   }
   ```

2. **suggest_improvements**
   ```json
   {
     "tool": "suggest_improvements",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)",
       "analysis": "SRP Analysis: The UserManager class has a single responsibility for user management."
     }
   }
   ```

3. **check_compliance**
   ```json
   {
     "tool": "check_compliance",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)",
       "principle": "Single Responsibility Principle"
     }
   }
   ```

4. **generate_tests**
   ```json
   {
     "tool": "generate_tests",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)",
       "analysis": "SRP Analysis: The UserManager class has a single responsibility for user management."
     }
   }
   ```

5. **refactor_code**
   ```json
   {
     "tool": "refactor_code",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)\n  def send_email(self, to, subject, body):\n    print(f'Sending email to {to}')",
       "principles": ["Single Responsibility Principle"]
     }
   }
   ```

### Orchestrator

Test each of the orchestrator tools:

1. **analyze_and_visualize**
   ```json
   {
     "tool": "analyze_and_visualize",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)\n  def send_email(self, to, subject, body):\n    print(f'Sending email to {to}')"
     }
   }
   ```

2. **generate_class_diagram**
   ```json
   {
     "tool": "generate_class_diagram",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)"
     }
   }
   ```

3. **create_documentation**
   ```json
   {
     "tool": "create_documentation",
     "params": {
       "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)"
     }
   }
   ```

## Testing with Claude Desktop

1. Add the servers to your `.claude-config.json` file as described in the main README.
2. Start Claude Desktop.
3. Create a new conversation and ask Claude to:
   - Generate a Mermaid diagram
   - Analyze code against SOLID principles
   - Create documentation with both analysis and diagrams

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Ensure your `ANTHROPIC_API_KEY` environment variable is set correctly.
   - Check that the API key is valid and has not expired.

2. **Connection Issues**
   - Verify all servers are running on the expected ports.
   - Check for any firewall or network restrictions that might prevent the servers from communicating.

3. **Dependency Issues**
   - Make sure all dependencies are installed: `pip install -e .`

4. **Docker Issues**
   - Ensure Docker is running on your system.
   - Check Docker logs for any container-specific errors: `docker-compose logs` 