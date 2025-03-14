# MCP SOLID Principles Analyzer

This MCP server provides tools for analyzing code against the SOLID principles of object-oriented design, suggesting improvements, checking compliance, and generating tests.

## SOLID Principles

The SOLID principles are a set of five design principles that help make software designs more understandable, flexible, and maintainable:

1. **S**ingle Responsibility Principle (SRP): A class should have only one reason to change.
2. **O**pen/Closed Principle (OCP): Software entities should be open for extension but closed for modification.
3. **L**iskov Substitution Principle (LSP): Objects of a superclass should be replaceable with objects of a subclass without affecting the correctness of the program.
4. **I**nterface Segregation Principle (ISP): No client should be forced to depend on methods it does not use.
5. **D**ependency Inversion Principle (DIP): High-level modules should not depend on low-level modules. Both should depend on abstractions.

## Features

- **Analyze code** against SOLID principles
- **Suggest improvements** based on SOLID analysis
- **Check compliance** with specific SOLID principles
- **Generate tests** to verify SOLID compliance

## Installation

### Using pip

```bash
pip install mcp-solid-server
```

### Using uvx

```bash
uvx mcp-server-solid
```

### From source

```bash
git clone https://github.com/sparesparrow/mcp-servers.git
cd mcp-servers
pip install -e .
```

## Usage

### Running the server

You can run the server directly:

```bash
python -m src.solid.solid_server
```

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)

## Tools

### analyze_code

Analyzes code for SOLID principles compliance.

```json
{
  "tool": "analyze_code",
  "params": {
    "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)\n  def render_profile(self, user_id):\n    return f'<div>{user_id}</div>'",
    "principles": ["Single Responsibility Principle", "Open/Closed Principle"]
  }
}
```

### suggest_improvements

Suggests code improvements based on SOLID analysis.

```json
{
  "tool": "suggest_improvements",
  "params": {
    "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)\n  def render_profile(self, user_id):\n    return f'<div>{user_id}</div>'",
    "analysis": "SRP Violation: UserManager handles both data operations and UI rendering."
  }
}
```

### check_compliance

Checks code compliance with a specific SOLID principle.

```json
{
  "tool": "check_compliance",
  "params": {
    "code": "class Bird:\n  def fly(self):\n    pass\n\nclass Penguin(Bird):\n  def fly(self):\n    raise Exception('Cannot fly')",
    "principle": "Liskov Substitution Principle"
  }
}
```

### generate_tests

Generates tests to verify SOLID compliance.

```json
{
  "tool": "generate_tests",
  "params": {
    "code": "class UserManager:\n  def __init__(self, db):\n    self.db = db\n  def create_user(self, username):\n    self.db.save('users', username)",
    "analysis": "SRP Analysis: UserManager has a single responsibility for user data operations."
  }
}
```

## Integration with Claude Desktop

To use this server with Claude Desktop, add the following to your `.claude-config.json` file:

```json
{
  "mcpServers": {
    "solid-analyzer": {
      "command": "python",
      "args": ["-m", "src.solid.solid_server"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

Alternatively, using Docker:

```json
{
  "mcpServers": {
    "solid-analyzer": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-solid-server"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

## Example Conversations

### Analyzing Code

**User**: "Can you analyze this Python class for SOLID principles?

```python
class OrderProcessor:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def process_order(self, order):
        # Save to database
        self.db.save('orders', order)
        
        # Send confirmation email
        self.send_email(order['email'], 'Order Confirmation', 'Your order has been processed')
        
        # Generate invoice PDF
        self.generate_invoice(order)
        
    def send_email(self, to, subject, body):
        # Code to send email
        print(f"Sending email to {to}")
        
    def generate_invoice(self, order):
        # Code to generate PDF
        print(f"Generating invoice for order {order['id']}")
```"

**Claude**: "Let me analyze this code against SOLID principles using my code analyzer."

*Claude uses the analyze_code tool*

**Claude**: "Here's my analysis of your OrderProcessor class:

## Single Responsibility Principle (SRP)
**Violation**: The OrderProcessor class handles multiple responsibilities:
1. Order processing logic
2. Email sending
3. Invoice generation

The SRP states that a class should have only one reason to change. This class would need to change if the order processing logic changes, if email sending requirements change, or if invoice generation changes.

## Open/Closed Principle (OCP)
**Concern**: The class is not easily extensible without modification. If you need to add additional steps to order processing (like adding loyalty points), you'd need to modify the existing class.

## Dependency Inversion Principle (DIP)
**Issue**: The class directly depends on concrete implementations rather than abstractions. The database connection is passed in, which is good, but email sending and invoice generation are hardcoded.

## Recommendations
1. Split the class into separate classes with single responsibilities:
   - OrderProcessor: Core order logic
   - EmailService: Handling email communications
   - InvoiceGenerator: Creating invoices

2. Use dependency injection for all dependencies:
```python
class OrderProcessor:
    def __init__(self, db_connection, email_service, invoice_generator):
        self.db = db_connection
        self.email_service = email_service
        self.invoice_generator = invoice_generator
    
    def process_order(self, order):
        # Save to database
        self.db.save('orders', order)
        
        # Send confirmation using email service
        self.email_service.send_confirmation(order)
        
        # Generate invoice using invoice generator
        self.invoice_generator.generate(order)
```

This refactoring would make each class focused on a single responsibility, easier to test, and more maintainable."

## Testing

Run the tests with pytest:

```bash
pytest tests/test_solid_server.py
```

## Docker

Build and run the Docker container:

```bash
docker build -t mcp-solid-server -f Dockerfile.solid .
docker run -i --rm -e ANTHROPIC_API_KEY=your_api_key mcp-solid-server
```

## License

MIT 