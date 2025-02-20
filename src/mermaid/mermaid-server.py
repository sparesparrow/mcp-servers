from mcp.server.fastmcp import FastMCP
import anthropic
import os
from typing import Optional

class MermaidServer:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Mermaid diagram generator server."""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.mcp = FastMCP("mermaid-generator")
        
        # Register tools
        self.setup_tools()
        
    def setup_tools(self):
        """Set up MCP tools."""
        @self.mcp.tool()
        def generate_diagram(query: str) -> str:
            """Generate a Mermaid diagram from a text description.
            
            Args:
                query: Text description of the diagram to generate
                
            Returns:
                str: Generated Mermaid diagram code
            """
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are an expert system designed to create Mermaid diagrams based on user queries. "
                       "Your task is to analyze the given input and generate a visual representation of the "
                       "concepts, relationships, or processes described. Return only the Mermaid diagram code "
                       "without any explanation.",
                messages=[{"role": "user", "content": query}]
            )
            return message.content[0].text

        @self.mcp.tool()
        def analyze_diagram(diagram: str) -> str:
            """Analyze a Mermaid diagram and provide insights.
            
            Args:
                diagram: Mermaid diagram code to analyze
                
            Returns:
                str: Analysis and insights about the diagram
            """
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are an expert in analyzing Mermaid diagrams. "
                       "Your task is to analyze the provided diagram code and provide insights about its "
                       "structure, clarity, and potential improvements.",
                messages=[{"role": "user", "content": f"Analyze this Mermaid diagram:\n\n{diagram}"}]
            )
            return message.content[0].text

        @self.mcp.tool()
        def modify_diagram(diagram: str, modification: str) -> str:
            """Modify an existing Mermaid diagram based on instructions.
            
            Args:
                diagram: Original Mermaid diagram code
                modification: Description of desired modifications
                
            Returns:
                str: Modified Mermaid diagram code
            """
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are an expert in modifying Mermaid diagrams. "
                       "Your task is to modify the provided diagram according to the requested changes "
                       "while maintaining its overall structure and clarity.",
                messages=[{
                    "role": "user",
                    "content": f"Modify this Mermaid diagram:\n\n{diagram}\n\nRequested changes:\n{modification}"
                }]
            )
            return message.content[0].text

    def run(self):
        """Run the MCP server."""
        self.mcp.run()

def main():
    """Main entry point."""
    server = MermaidServer()
    server.run()

if __name__ == "__main__":
    main()
