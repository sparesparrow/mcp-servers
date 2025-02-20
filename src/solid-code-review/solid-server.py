from mcp.server.fastmcp import FastMCP
import anthropic
import os
from typing import Optional, List, Dict
from enum import Enum
from dataclasses import dataclass

class SolidPrinciple(str, Enum):
    SRP = "Single Responsibility Principle"
    OCP = "Open/Closed Principle"
    LSP = "Liskov Substitution Principle"
    ISP = "Interface Segregation Principle"
    DIP = "Dependency Inversion Principle"

@dataclass
class CodeAnalysis:
    """Analysis results for a code segment."""
    principle: SolidPrinciple
    violations: List[str]
    recommendations: List[str]
    code_suggestions: Dict[str, str]

class SolidServer:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the SOLID analyzer server."""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.mcp = FastMCP("solid-analyzer")
        
        # Register tools
        self.setup_tools()
        
    def setup_tools(self):
        """Set up MCP tools."""
        @self.mcp.tool()
        def analyze_code(code: str, principles: Optional[List[str]] = None) -> str:
            """Analyze code for SOLID principles compliance.
            
            Args:
                code: Code to analyze
                principles: Optional list of specific principles to check
                
            Returns:
                str: Analysis results in structured format
            """
            principles = principles or [p.value for p in SolidPrinciple]
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a SOLID principles expert. Analyze code for adherence to SOLID principles "
                       "and provide specific, actionable recommendations for improvement. Focus on practical "
                       "solutions that maintain existing functionality while improving code structure.",
                messages=[{
                    "role": "user",
                    "content": f"Analyze this code for the following SOLID principles: {', '.join(principles)}\n\n{code}"
                }]
            )
            return message.content[0].text

        @self.mcp.tool()
        def suggest_improvements(code: str, analysis: str) -> str:
            """Suggest code improvements based on SOLID analysis.
            
            Args:
                code: Original code
                analysis: Analysis results from analyze_code
                
            Returns:
                str: Improved code with explanations
            """
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a SOLID principles expert. Based on the provided analysis, "
                       "suggest specific code improvements that address identified issues while "
                       "maintaining functionality. Provide both the improved code and explanations "
                       "of the changes made.",
                messages=[{
                    "role": "user",
                    "content": f"Original code:\n\n{code}\n\nAnalysis:\n\n{analysis}\n\n"
                              "Please provide improved code and explain the changes."
                }]
            )
            return message.content[0].text

        @self.mcp.tool()
        def check_compliance(code: str, principle: str) -> str:
            """Check code compliance with a specific SOLID principle.
            
            Args:
                code: Code to check
                principle: Specific SOLID principle to verify
                
            Returns:
                str: Compliance assessment and recommendations
            """
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system=f"You are a SOLID principles expert focusing on the {principle}. "
                       "Your task is to thoroughly assess the provided code's compliance with "
                       "this principle and provide specific recommendations for improvement.",
                messages=[{
                    "role": "user",
                    "content": f"Assess this code's compliance with {principle}:\n\n{code}"
                }]
            )
            return message.content[0].text

        @self.mcp.tool()
        def generate_tests(code: str, analysis: str) -> str:
            """Generate tests to verify SOLID compliance.
            
            Args:
                code: Code to test
                analysis: Analysis results from analyze_code
                
            Returns:
                str: Generated test cases
            """
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a testing expert focusing on SOLID principles. "
                       "Your task is to generate comprehensive test cases that verify "
                       "the code's compliance with SOLID principles and catch potential violations.",
                messages=[{
                    "role": "user",
                    "content": f"Generate tests for this code based on the analysis:\n\n"
                              f"Code:\n{code}\n\nAnalysis:\n{analysis}"
                }]
            )
            return message.content[0].text

    def run(self):
        """Run the MCP server."""
        self.mcp.run()

def main():
    """Main entry point."""
    server = SolidServer()
    server.run()

if __name__ == "__main__":
    main()
