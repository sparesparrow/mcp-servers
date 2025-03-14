from mcp.server.fastmcp import FastMCP
import anthropic
import os
import logging
import hashlib
import json
import time
import threading
from typing import Optional, List, Dict, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solid-server')

class SolidError(Exception):
    """Base exception class for SOLID server errors."""
    pass

class ApiError(SolidError):
    """Exception raised for API-related errors."""
    pass

class RateLimitError(SolidError):
    """Exception raised when rate limit is exceeded."""
    pass

class ValidationError(SolidError):
    """Exception raised when input code validation fails."""
    pass

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

class Cache:
    """Simple cache implementation with TTL support."""
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache with TTL in seconds."""
        self.cache = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Tuple of (hit, value) where hit is True if cache hit
        """
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                logger.debug(f"Cache hit for key {key[:8]}...")
                return True, value
        return False, None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = (time.time(), value)
        logger.debug(f"Cache set for key {key[:8]}...")
    
    def invalidate(self, key: str) -> None:
        """
        Remove key from cache.
        
        Args:
            key: Cache key to remove
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache invalidated for key {key[:8]}...")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache = {}
        logger.debug("Cache cleared")

class RateLimiter:
    """Rate limiter to control API call frequency."""
    def __init__(self, calls_per_minute: int = 25):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum number of calls allowed per minute
        """
        self.calls_per_minute = calls_per_minute
        self.call_history: List[float] = []
        self.lock = threading.Lock()
    
    def can_make_call(self) -> bool:
        """
        Check if a call can be made without exceeding the rate limit.
        
        Returns:
            bool: True if a call can be made, False otherwise
        """
        with self.lock:
            now = time.time()
            # Remove timestamps older than 1 minute
            self.call_history = [t for t in self.call_history if now - t < 60]
            return len(self.call_history) < self.calls_per_minute
    
    def record_call(self) -> None:
        """Record that a call was made."""
        with self.lock:
            self.call_history.append(time.time())
    
    def wait_if_needed(self) -> None:
        """
        Wait if rate limit is reached.
        
        Raises:
            RateLimitError: If rate limit is exceeded and can't wait
        """
        with self.lock:
            now = time.time()
            # Remove timestamps older than 1 minute
            self.call_history = [t for t in self.call_history if now - t < 60]
            
            if len(self.call_history) >= self.calls_per_minute:
                # Need to wait - calculate delay
                oldest_call = min(self.call_history)
                wait_time = 60 - (now - oldest_call)
                
                # Add a small buffer
                wait_time += 1
                
                if wait_time > 10:  # If wait time is too long, raise error instead
                    raise RateLimitError(f"Rate limit exceeded. Would need to wait {wait_time:.1f} seconds.")
                
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)

class CodeValidator:
    """Simple validator for code syntax and structure."""
    
    @staticmethod
    def validate_language(code: str) -> Optional[str]:
        """
        Attempt to determine the programming language from code.
        
        Args:
            code: Source code to analyze
            
        Returns:
            String language identifier or None if couldn't determine
        """
        # Simple heuristics to guess the language
        if 'def ' in code and ('self' in code or '__init__' in code) and ':' in code:
            return 'python'
        elif '{' in code and '}' in code and ('class ' in code or 'interface ' in code or 'function ' in code):
            if 'func ' in code or 'struct ' in code:
                return 'go'
            elif 'fun ' in code:
                return 'kotlin'
            elif 'import java.' in code or 'public class' in code:
                return 'java'
            elif 'namespace ' in code or 'using System' in code:
                return 'csharp'
            else:
                return 'typescript' if 'interface ' in code and ':' in code else 'javascript'
        
        return None
    
    @staticmethod
    def validate_basic_syntax(code: str) -> Dict[str, Any]:
        """
        Perform basic syntax validation on code.
        
        Args:
            code: Source code to validate
            
        Returns:
            Dict with validation results
        """
        issues = []
        language = CodeValidator.validate_language(code)
        
        # Check for balanced elements
        if code.count('{') != code.count('}'):
            issues.append("Unbalanced curly braces { }")
        if code.count('(') != code.count(')'):
            issues.append("Unbalanced parentheses ( )")
        if code.count('[') != code.count(']'):
            issues.append("Unbalanced square brackets [ ]")
        
        # Language-specific checks
        if language == 'python':
            # Check for indentation consistency
            lines = code.split('\n')
            indentation_levels = set()
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    spaces = len(line) - len(line.lstrip())
                    if spaces > 0:
                        indentation_levels.add(spaces)
            
            if len(indentation_levels) > 1 and 2 in indentation_levels and 4 in indentation_levels:
                issues.append("Inconsistent indentation (mix of 2 and 4 spaces)")
        
        # Check for potential empty definitions
        if language == 'python' and 'def ' in code and 'pass' not in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'def ' in line and i + 1 < len(lines) and not lines[i+1].strip():
                    issues.append(f"Empty function definition at line {i+1}: {line.strip()}")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "language": language
        }

class SolidServer:
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 3600, calls_per_minute: int = 25):
        """Initialize the SOLID analyzer server."""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.mcp = FastMCP("solid-analyzer")
        self.cache = Cache(ttl_seconds=cache_ttl)
        self.rate_limiter = RateLimiter(calls_per_minute=calls_per_minute)
        self.validator = CodeValidator()
        
        # Register tools
        self.setup_tools()
        
    def setup_tools(self):
        """Set up MCP tools."""
        self.analyze_code = self._register_analyze_code()
        self.suggest_improvements = self._register_suggest_improvements()
        self.check_compliance = self._register_check_compliance()
        self.generate_tests = self._register_generate_tests()
        self.refactor_code = self._register_refactor_code()
        self.clear_cache = self._register_clear_cache()
        self.get_status = self._register_get_status()
    
    def _handle_api_call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Handle API calls with error handling, rate limiting, and logging.
        
        Args:
            func: The API function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: The result of the API call
            
        Raises:
            ApiError: If the API call fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            # Check rate limit
            self.rate_limiter.wait_if_needed()
            
            # Make the API call
            logger.info(f"Making API call to {func.__name__}")
            result = func(*args, **kwargs)
            
            # Record the call
            self.rate_limiter.record_call()
            
            logger.info(f"API call to {func.__name__} successful")
            return result
        except RateLimitError as e:
            raise
        except anthropic.APIError as e:
            error_msg = f"Anthropic API Error: {str(e)}"
            logger.error(error_msg)
            raise ApiError(error_msg) from e
        except anthropic.RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            raise ApiError(error_msg) from e
        except anthropic.AuthenticationError as e:
            error_msg = f"Authentication error: {str(e)}"
            logger.error(error_msg)
            raise ApiError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            raise SolidError(error_msg) from e
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a cache key from a prefix and kwargs.
        
        Args:
            prefix: Prefix for the cache key
            **kwargs: Key-value pairs to include in the key
            
        Returns:
            str: Cache key
        """
        # Create a normalized string from kwargs
        kwargs_str = json.dumps(kwargs, sort_keys=True)
        # Generate hash
        return f"{prefix}:{hashlib.md5(kwargs_str.encode('utf-8')).hexdigest()}"
    
    def _validate_code(self, code: str) -> None:
        """
        Validate code for basic syntax.
        
        Args:
            code: Code to validate
            
        Raises:
            ValidationError: If code is invalid
        """
        validation = CodeValidator.validate_basic_syntax(code)
        if not validation["is_valid"]:
            issues_str = "\n".join([f"- {issue}" for issue in validation["issues"]])
            error_msg = f"Invalid code syntax. Please fix the following issues:\n{issues_str}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
    
    def _register_analyze_code(self):
        """Register the analyze_code tool."""
        @self.mcp.tool()
        def analyze_code(code: str, principles: Optional[List[str]] = None) -> str:
            """Analyze code for SOLID principles compliance.
            
            Args:
                code: Code to analyze
                principles: Optional list of specific principles to check
                
            Returns:
                str: Analysis results in structured format
            """
            if not code or not code.strip():
                error_msg = "Code cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Basic code validation
            try:
                self._validate_code(code)
            except ValidationError as e:
                # For analysis, we'll just log validation issues but continue
                logger.warning(f"Code validation issues: {str(e)}")
                
            principles = principles or [p.value for p in SolidPrinciple]
            
            # Validate principles
            valid_principles = [p.value for p in SolidPrinciple]
            for principle in principles:
                if principle not in valid_principles:
                    error_msg = f"Invalid principle: {principle}. Must be one of: {', '.join(valid_principles)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            # Check cache first
            cache_key = self._generate_cache_key("analyze_code", code=code, principles=principles)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for analyze_code")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for analyze_code")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a SOLID principles expert. Analyze code for adherence to SOLID principles "
                       "and provide specific, actionable recommendations for improvement. Focus on practical "
                       "solutions that maintain existing functionality while improving code structure. "
                       "Provide your analysis in a structured format with sections for each principle, "
                       "clearly identifying violations and recommendations.",
                messages=[{
                    "role": "user",
                    "content": f"Analyze this code for the following SOLID principles: {', '.join(principles)}\n\n{code}"
                }]
            )
            
            result = message.content[0].text
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return analyze_code

    def _register_suggest_improvements(self):
        """Register the suggest_improvements tool."""
        @self.mcp.tool()
        def suggest_improvements(code: str, analysis: str) -> str:
            """Suggest code improvements based on SOLID analysis.
            
            Args:
                code: Original code
                analysis: Analysis results from analyze_code
                
            Returns:
                str: Improved code with explanations
            """
            if not code or not code.strip():
                error_msg = "Code cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not analysis or not analysis.strip():
                error_msg = "Analysis cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Basic code validation
            try:
                self._validate_code(code)
            except ValidationError as e:
                # For suggestions, we'll just log validation issues but continue
                logger.warning(f"Code validation issues: {str(e)}")
            
            # Check cache first
            cache_key = self._generate_cache_key("suggest_improvements", code=code, analysis=analysis)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for suggest_improvements")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for suggest_improvements")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a SOLID principles expert. Based on the provided analysis, "
                       "suggest specific code improvements that address identified issues while "
                       "maintaining functionality. Provide both the improved code and explanations "
                       "of the changes made. Group improvements by SOLID principle to make them easier "
                       "to understand and implement.",
                messages=[{
                    "role": "user",
                    "content": f"Original code:\n\n{code}\n\nAnalysis:\n\n{analysis}\n\n"
                              "Please provide improved code and explain the changes."
                }]
            )
            
            result = message.content[0].text
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return suggest_improvements

    def _register_check_compliance(self):
        """Register the check_compliance tool."""
        @self.mcp.tool()
        def check_compliance(code: str, principle: str) -> str:
            """Check code compliance with a specific SOLID principle.
            
            Args:
                code: Code to check
                principle: Specific SOLID principle to verify
                
            Returns:
                str: Compliance assessment and recommendations
            """
            if not code or not code.strip():
                error_msg = "Code cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Validate principle
            valid_principles = [p.value for p in SolidPrinciple]
            if principle not in valid_principles:
                error_msg = f"Invalid principle: {principle}. Must be one of: {', '.join(valid_principles)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Basic code validation
            try:
                self._validate_code(code)
            except ValidationError as e:
                # For compliance checks, we'll just log validation issues but continue
                logger.warning(f"Code validation issues: {str(e)}")
            
            # Check cache first
            cache_key = self._generate_cache_key("check_compliance", code=code, principle=principle)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for check_compliance with principle: {principle}")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for check_compliance with principle: {principle}")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system=f"You are a SOLID principles expert focusing on the {principle}. "
                       "Your task is to thoroughly assess the provided code's compliance with "
                       "this principle and provide specific recommendations for improvement. "
                       "Include a compliance score from 0-10 and specific code examples of violations.",
                messages=[{
                    "role": "user",
                    "content": f"Assess this code's compliance with {principle}:\n\n{code}"
                }]
            )
            
            result = message.content[0].text
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return check_compliance

    def _register_generate_tests(self):
        """Register the generate_tests tool."""
        @self.mcp.tool()
        def generate_tests(code: str, analysis: str) -> str:
            """Generate tests to verify SOLID compliance.
            
            Args:
                code: Code to test
                analysis: Analysis results from analyze_code
                
            Returns:
                str: Generated test cases
            """
            if not code or not code.strip():
                error_msg = "Code cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not analysis or not analysis.strip():
                error_msg = "Analysis cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Basic code validation
            try:
                self._validate_code(code)
            except ValidationError as e:
                # For test generation, we'll just log validation issues but continue
                logger.warning(f"Code validation issues: {str(e)}")
            
            # Check cache first
            cache_key = self._generate_cache_key("generate_tests", code=code, analysis=analysis)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for generate_tests")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for generate_tests")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a testing expert focusing on SOLID principles. "
                       "Your task is to generate comprehensive test cases that verify "
                       "the code's compliance with SOLID principles and catch potential violations. "
                       "Focus on creating tests that will fail if SOLID principles are violated.",
                messages=[{
                    "role": "user",
                    "content": f"Generate tests for this code based on the analysis:\n\n"
                              f"Code:\n{code}\n\nAnalysis:\n{analysis}"
                }]
            )
            
            result = message.content[0].text
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return generate_tests
        
    def _register_refactor_code(self):
        """Register the refactor_code tool."""
        @self.mcp.tool()
        def refactor_code(code: str, principles: Optional[List[str]] = None) -> Dict[str, Any]:
            """Refactor code based on SOLID principles and return improved version.
            
            Args:
                code: Original code to refactor
                principles: Optional list of specific principles to focus on
                
            Returns:
                Dict with refactored code and explanations
            """
            if not code or not code.strip():
                error_msg = "Code cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Basic code validation
            try:
                self._validate_code(code)
            except ValidationError as e:
                error_msg = f"Cannot refactor code with syntax issues: {str(e)}"
                logger.error(error_msg)
                raise ValidationError(error_msg)
                
            principles = principles or [p.value for p in SolidPrinciple]
            
            # Validate principles
            valid_principles = [p.value for p in SolidPrinciple]
            for principle in principles:
                if principle not in valid_principles:
                    error_msg = f"Invalid principle: {principle}. Must be one of: {', '.join(valid_principles)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
            # First analyze the code to understand issues
            logger.info(f"Analyzing code before refactoring")
            analysis = analyze_code(code, principles)
            
            # Check cache for the refactoring
            cache_key = self._generate_cache_key("refactor_code", code=code, principles=principles)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for refactor_code")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for refactor_code")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are a code refactoring expert specializing in SOLID principles. "
                       "Your task is to refactor the provided code to better adhere to SOLID principles. "
                       "Provide both the refactored code and a clear explanation of the changes made. "
                       "Ensure the refactored code maintains the same functionality while improving its structure. "
                       "Focus on making practical, maintainable improvements.",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Refactor this code to better adhere to these SOLID principles: {', '.join(principles)}\n\n"
                        f"Original code:\n\n{code}\n\n"
                        f"Analysis of issues:\n\n{analysis}\n\n"
                        "Please provide the refactored code and explain your changes."
                    )
                }]
            )
            
            # Parse the response to extract code and explanations
            content = message.content[0].text
            
            # Basic parsing of response to extract code blocks and explanations
            code_blocks = []
            explanations = []
            
            # Look for code blocks in markdown format
            lines = content.split('\n')
            in_code_block = False
            current_block = []
            
            for line in lines:
                if line.strip().startswith('```') and not in_code_block:
                    in_code_block = True
                    current_block = []
                elif line.strip().startswith('```') and in_code_block:
                    in_code_block = False
                    code_blocks.append('\n'.join(current_block))
                elif in_code_block:
                    current_block.append(line)
                elif line.strip() and not in_code_block:
                    explanations.append(line)
            
            # Extract the main refactored code (usually the largest code block)
            refactored_code = max(code_blocks, key=len) if code_blocks else ""
            
            # Create the result
            result = {
                "refactored_code": refactored_code,
                "explanations": '\n'.join(explanations),
                "principles_addressed": principles,
                "full_response": content
            }
            
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return refactor_code
        
    def _register_clear_cache(self):
        """Register a tool to clear the cache."""
        @self.mcp.tool()
        def clear_cache() -> str:
            """Clear the server's response cache.
            
            Returns:
                str: Confirmation message
            """
            old_size = len(self.cache.cache)
            self.cache.clear()
            return f"Cache cleared successfully. {old_size} entries removed."
        
        return clear_cache
        
    def _register_get_status(self):
        """Register a tool to get server status."""
        @self.mcp.tool()
        def get_status() -> Dict[str, Any]:
            """Get the current server status.
            
            Returns:
                Dict containing status information
            """
            # Calculate stats
            cache_size = len(self.cache.cache)
            cache_entries = [key for key in self.cache.cache]
            
            # Rate limit info
            now = time.time()
            recent_calls = [t for t in self.rate_limiter.call_history if now - t < 60]
            calls_remaining = self.rate_limiter.calls_per_minute - len(recent_calls)
            
            return {
                "cache": {
                    "size": cache_size,
                    "ttl_seconds": self.cache.ttl_seconds,
                    "entry_prefixes": [key.split(":")[0] for key in cache_entries[:10]] if cache_entries else []
                },
                "rate_limiting": {
                    "calls_per_minute": self.rate_limiter.calls_per_minute,
                    "calls_in_last_minute": len(recent_calls),
                    "calls_remaining": calls_remaining
                }
            }
        
        return get_status

    def run(self):
        """Run the MCP server."""
        logger.info("Starting SOLID MCP server")
        self.mcp.run()

def main():
    """Main entry point."""
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY environment variable not set.")
        logger.warning("The server will fail to process requests without a valid API key.")
    
    # Get cache TTL from environment or use default (1 hour)
    cache_ttl = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
    
    # Get rate limit from environment or use default (25 calls per minute)
    calls_per_minute = int(os.environ.get("CALLS_PER_MINUTE", "25"))
    
    server = SolidServer(cache_ttl=cache_ttl, calls_per_minute=calls_per_minute)
    server.run()

if __name__ == "__main__":
    main()
