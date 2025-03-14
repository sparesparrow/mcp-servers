from mcp.server.fastmcp import FastMCP
import anthropic
import os
import logging
import hashlib
import json
import time
import threading
import re
import base64
import io
import requests
from functools import lru_cache
from typing import Optional, Any, Dict, Callable, Tuple, List

# Define common color themes
DEFAULT_COLOR_THEMES = {
    "default": {
        "node_fill": "#f9f9f9",
        "node_border": "#333333",
        "node_text": "#333333",
        "edge": "#666666",
        "highlight": "#ff7700",
        "success": "#00aa00",
        "warning": "#ffaa00",
        "error": "#dd0000"
    },
    "dark": {
        "node_fill": "#2d2d2d",
        "node_border": "#aaaaaa",
        "node_text": "#ffffff",
        "edge": "#888888",
        "highlight": "#ff9933",
        "success": "#00cc00",
        "warning": "#ffcc00",
        "error": "#ff4444"
    },
    "pastel": {
        "node_fill": "#f0f8ff",
        "node_border": "#6699cc",
        "node_text": "#336699",
        "edge": "#6699cc",
        "highlight": "#ff9966",
        "success": "#99cc99",
        "warning": "#ffcc99",
        "error": "#ff9999"
    },
    "vibrant": {
        "node_fill": "#ffffff",
        "node_border": "#4a86e8",
        "node_text": "#333333",
        "edge": "#6d9eeb",
        "highlight": "#ff7700",
        "success": "#6aa84f",
        "warning": "#f1c232",
        "error": "#cc0000"
    }
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mermaid-server')

class MermaidError(Exception):
    """Base exception class for Mermaid server errors."""
    pass

class ApiError(MermaidError):
    """Exception raised for API-related errors."""
    pass

class RateLimitError(MermaidError):
    """Exception raised when rate limit is exceeded."""
    pass

class ValidationError(MermaidError):
    """Exception raised when Mermaid syntax is invalid."""
    pass

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

class MermaidValidator:
    """Validator for Mermaid diagram syntax."""
    
    # Define diagram types and their specific validation patterns
    DIAGRAM_TYPES = {
        'graph': r'^graph\s+(TD|TB|BT|RL|LR)',
        'flowchart': r'^flowchart\s+(TD|TB|BT|RL|LR)',
        'sequenceDiagram': r'^sequenceDiagram',
        'classDiagram': r'^classDiagram',
        'stateDiagram': r'^stateDiagram(-v2)?',
        'erDiagram': r'^erDiagram',
        'gantt': r'^gantt',
        'pie': r'^pie',
        'journey': r'^journey',
        'requirement': r'^requirement',
        'gitGraph': r'^gitGraph'
    }
    
    @staticmethod
    def validate(diagram: str) -> Dict[str, Any]:
        """
        Validate Mermaid diagram syntax.
        
        Args:
            diagram: Mermaid diagram code to validate
            
        Returns:
            Dict with validation results including is_valid flag and issues list
        """
        if not diagram or not diagram.strip():
            return {
                "is_valid": False,
                "issues": ["Diagram is empty"],
                "diagram_type": None
            }
        
        # Clean the diagram text
        diagram = diagram.strip()
        
        # Remove markdown code fences if present
        if diagram.startswith("```mermaid"):
            diagram = "\n".join(diagram.split("\n")[1:])
        if diagram.endswith("```"):
            diagram = "\n".join(diagram.split("\n")[:-1])
        
        diagram = diagram.strip()
        
        issues = []
        diagram_type = None
        
        # Check for valid diagram type
        for dtype, pattern in MermaidValidator.DIAGRAM_TYPES.items():
            if re.search(pattern, diagram, re.MULTILINE):
                diagram_type = dtype
                break
        
        if not diagram_type:
            issues.append("Missing or invalid diagram type. Must start with a valid diagram declaration (e.g., 'graph TD', 'sequenceDiagram')")
        
        # Check for balanced brackets, parentheses, and quotes
        if diagram.count('[') != diagram.count(']'):
            issues.append("Unbalanced square brackets [ ]")
        if diagram.count('(') != diagram.count(')'):
            issues.append("Unbalanced parentheses ( )")
        if diagram.count('{') != diagram.count('}'):
            issues.append("Unbalanced curly braces { }")
        
        # Check for open double quotes
        if diagram.count('"') % 2 != 0:
            issues.append("Unbalanced double quotes")
        
        # Diagram-specific validations
        if diagram_type == 'graph' or diagram_type == 'flowchart':
            # Check for node definitions without connections
            lines = diagram.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if (re.match(r'^[A-Za-z0-9_-]+\s*\[', line) and 
                    not any(re.search(r'[A-Za-z0-9_-]+\s*(-+>|<-+|--)\s*[A-Za-z0-9_-]+', l) for l in lines)):
                    issues.append(f"Node defined but not connected to any other node at line {i+1}: {line}")
        
        elif diagram_type == 'sequenceDiagram':
            # Check for actors/participants
            if not re.search(r'(actor|participant)\s+[A-Za-z0-9_-]+', diagram, re.MULTILINE):
                issues.append("No actors or participants defined in sequence diagram")
        
        # Return validation results
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "diagram_type": diagram_type
        }

class StyleManager:
    """Manages styling and colors for Mermaid diagrams."""
    
    def __init__(self, default_theme: str = "default", custom_themes_path: Optional[str] = None):
        """
        Initialize the style manager.
        
        Args:
            default_theme: The default color theme to use
            custom_themes_path: Path to JSON file containing custom themes
        """
        self.themes = DEFAULT_COLOR_THEMES.copy()
        self.custom_themes_path = custom_themes_path or os.path.expanduser("~/.mermaid_themes.json")
        self._load_custom_themes()
        self.default_theme = default_theme if default_theme in self.themes else "default"
        logger.info(f"StyleManager initialized with default theme: {self.default_theme}")
    
    def _load_custom_themes(self) -> None:
        """Load custom themes from file."""
        if os.path.exists(self.custom_themes_path):
            try:
                with open(self.custom_themes_path, 'r') as f:
                    custom_themes = json.load(f)
                # Validate and add each custom theme
                for theme_name, theme_colors in custom_themes.items():
                    if self._validate_theme(theme_colors):
                        self.themes[theme_name] = theme_colors
                        logger.info(f"Loaded custom theme: {theme_name}")
                    else:
                        logger.warning(f"Custom theme '{theme_name}' has invalid format and was not loaded")
            except Exception as e:
                logger.error(f"Error loading custom themes: {str(e)}")
    
    def _save_custom_themes(self) -> None:
        """Save custom themes to file."""
        try:
            # Determine which themes are custom (not in DEFAULT_COLOR_THEMES)
            custom_themes = {k: v for k, v in self.themes.items() if k not in DEFAULT_COLOR_THEMES}
            if custom_themes:
                with open(self.custom_themes_path, 'w') as f:
                    json.dump(custom_themes, f, indent=2)
                logger.info(f"Saved {len(custom_themes)} custom themes to {self.custom_themes_path}")
        except Exception as e:
            logger.error(f"Error saving custom themes: {str(e)}")
    
    def _validate_theme(self, theme: Dict[str, str]) -> bool:
        """
        Validate theme structure.
        
        Args:
            theme: Theme colors dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_keys = [
            "node_fill", "node_border", "node_text", "edge", 
            "highlight", "success", "warning", "error"
        ]
        
        # Check that all required keys are present
        if not all(key in theme for key in required_keys):
            return False
            
        # Check that all values are valid hex colors
        hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        return all(hex_pattern.match(theme[key]) for key in required_keys)
    
    def add_custom_theme(self, name: str, colors: Dict[str, str]) -> bool:
        """
        Add a new custom theme.
        
        Args:
            name: Name for the new theme
            colors: Dictionary of color values
            
        Returns:
            bool: True if theme was added successfully
        """
        # Prevent overwriting built-in themes
        if name in DEFAULT_COLOR_THEMES:
            logger.warning(f"Cannot override built-in theme '{name}'")
            return False
            
        # Validate theme
        if not self._validate_theme(colors):
            logger.warning(f"Theme validation failed for '{name}'")
            return False
            
        # Add theme
        self.themes[name] = colors
        self._save_custom_themes()
        logger.info(f"Added custom theme: {name}")
        return True
    
    def remove_custom_theme(self, name: str) -> bool:
        """
        Remove a custom theme.
        
        Args:
            name: Name of theme to remove
            
        Returns:
            bool: True if theme was removed
        """
        # Cannot remove built-in themes
        if name in DEFAULT_COLOR_THEMES:
            logger.warning(f"Cannot remove built-in theme '{name}'")
            return False
            
        # Remove if exists
        if name in self.themes:
            del self.themes[name]
            self._save_custom_themes()
            logger.info(f"Removed custom theme: {name}")
            
            # Reset default theme if it was removed
            if self.default_theme == name:
                self.default_theme = "default"
                logger.info(f"Reset default theme to 'default'")
                
            return True
        else:
            logger.warning(f"Theme '{name}' not found")
            return False
    
    def get_theme(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get a color theme by name.
        
        Args:
            theme_name: Name of the theme to get, or None for default theme
            
        Returns:
            Dict of color names to hex values
        """
        theme = theme_name if theme_name and theme_name in self.themes else self.default_theme
        return self.themes[theme]
    
    def add_styling_to_diagram(self, diagram: str, theme_name: Optional[str] = None) -> str:
        """
        Add styling to a Mermaid diagram.
        
        Args:
            diagram: The Mermaid diagram code
            theme_name: Name of the theme to use (optional)
            
        Returns:
            The diagram with styling applied
        """
        theme = self.get_theme(theme_name)
        
        # Extract diagram type from the first line
        lines = diagram.strip().split('\n')
        if not lines:
            return diagram
            
        diagram_type = lines[0].strip().lower()
        
        if diagram_type.startswith('graph') or diagram_type.startswith('flowchart'):
            # For flowcharts/graphs
            return self._style_flowchart(diagram, theme)
        elif diagram_type.startswith('sequencediagram'):
            # For sequence diagrams
            return self._style_sequence_diagram(diagram, theme)
        elif diagram_type.startswith('classDiagram'):
            # For class diagrams
            return self._style_class_diagram(diagram, theme)
        elif diagram_type.startswith('erdiagram'):
            # For ER diagrams
            return self._style_er_diagram(diagram, theme)
        else:
            # Default - just return original diagram for unsupported types
            logger.warning(f"Styling not supported for diagram type: {diagram_type}")
            return diagram
    
    def _style_flowchart(self, diagram: str, theme: Dict[str, str]) -> str:
        """Add styling to a flowchart/graph diagram."""
        # Check if the diagram already has styling
        if "style " in diagram or "classDef " in diagram:
            logger.info("Diagram already contains styling, skipping auto-styling")
            return diagram
            
        lines = diagram.strip().split('\n')
        styled_lines = lines.copy()
        
        # Get all node IDs
        node_pattern = re.compile(r'^\s*([A-Za-z0-9_-]+)')
        node_ids = set()
        
        for line in lines:
            # Skip lines that are not node definitions
            if '-->' in line or '---' in line or '===' in line:
                continue
                
            match = node_pattern.match(line)
            if match:
                node_id = match.group(1)
                if node_id not in ('graph', 'flowchart', 'subgraph'):
                    node_ids.add(node_id)
        
        # Add styling section at the end
        styled_lines.append("")
        styled_lines.append("%% Styling")
        styled_lines.append(f"classDef default fill:{theme['node_fill']},stroke:{theme['node_border']},stroke-width:1px,color:{theme['node_text']},rx:5px,ry:5px")
        styled_lines.append(f"classDef highlight fill:{theme['highlight']},stroke:{theme['node_border']},stroke-width:2px,color:white,rx:5px,ry:5px")
        styled_lines.append(f"classDef success fill:{theme['success']},stroke:{theme['node_border']},stroke-width:1px,color:white,rx:5px,ry:5px")
        styled_lines.append(f"classDef warning fill:{theme['warning']},stroke:{theme['node_border']},stroke-width:1px,color:{theme['node_text']},rx:5px,ry:5px")
        styled_lines.append(f"classDef error fill:{theme['error']},stroke:{theme['node_border']},stroke-width:1px,color:white,rx:5px,ry:5px")
        
        return '\n'.join(styled_lines)
    
    def _style_sequence_diagram(self, diagram: str, theme: Dict[str, str]) -> str:
        """Add styling to a sequence diagram."""
        if "%%{init:" in diagram:
            logger.info("Diagram already contains init styling, skipping auto-styling")
            return diagram
            
        # For sequence diagrams, we add styling at the beginning
        init_config = f"""%%{{init: {{
            'theme': 'base',
            'themeVariables': {{
                'primaryColor': '{theme["highlight"]}',
                'primaryTextColor': '#fff',
                'primaryBorderColor': '{theme["node_border"]}',
                'lineColor': '{theme["edge"]}',
                'secondaryColor': '{theme["node_fill"]}',
                'tertiaryColor': '{theme["node_fill"]}'
            }}
        }} }}%%
"""
        return init_config + diagram
    
    def _style_class_diagram(self, diagram: str, theme: Dict[str, str]) -> str:
        """Add styling to a class diagram."""
        if "%%{init:" in diagram:
            logger.info("Diagram already contains init styling, skipping auto-styling")
            return diagram
            
        # For class diagrams, we add styling at the beginning
        init_config = f"""%%{{init: {{
            'theme': 'base',
            'themeVariables': {{
                'primaryColor': '{theme["highlight"]}',
                'primaryTextColor': '#fff',
                'primaryBorderColor': '{theme["node_border"]}',
                'lineColor': '{theme["edge"]}',
                'secondaryColor': '{theme["node_fill"]}',
                'tertiaryColor': '{theme["node_fill"]}'
            }}
        }} }}%%
"""
        return init_config + diagram
    
    def _style_er_diagram(self, diagram: str, theme: Dict[str, str]) -> str:
        """Add styling to an ER diagram."""
        if "%%{init:" in diagram:
            logger.info("Diagram already contains init styling, skipping auto-styling")
            return diagram
            
        # For ER diagrams, we add styling at the beginning
        init_config = f"""%%{{init: {{
            'theme': 'base',
            'themeVariables': {{
                'primaryColor': '{theme["highlight"]}',
                'primaryTextColor': '#fff',
                'primaryBorderColor': '{theme["node_border"]}',
                'lineColor': '{theme["edge"]}',
                'secondaryColor': '{theme["node_fill"]}',
                'tertiaryColor': '{theme["node_fill"]}'
            }}
        }} }}%%
"""
        return init_config + diagram

class MermaidServer:
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 3600, calls_per_minute: int = 25, default_theme: str = "default", custom_themes_path: Optional[str] = None):
        """Initialize the Mermaid diagram generator server."""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.mcp = FastMCP("mermaid-generator")
        self.cache = Cache(ttl_seconds=cache_ttl)
        self.rate_limiter = RateLimiter(calls_per_minute=calls_per_minute)
        self.validator = MermaidValidator()
        self.style_manager = StyleManager(default_theme=default_theme, custom_themes_path=custom_themes_path)
        
        # Register tools
        self.setup_tools()
        
    def setup_tools(self):
        """Set up MCP tools."""
        self.generate_diagram = self._register_generate_diagram()
        self.analyze_diagram = self._register_analyze_diagram()
        self.modify_diagram = self._register_modify_diagram()
        self.validate_diagram = self._register_validate_diagram()
        self.preview_diagram = self._register_preview_diagram()
        self.clear_cache = self._register_clear_cache()
        self.get_status = self._register_get_status()
        self.get_theme_info = self._register_get_theme_info()
        self.add_custom_theme = self._register_add_custom_theme()
        self.remove_custom_theme = self._register_remove_custom_theme()
    
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
            raise MermaidError(error_msg) from e

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
    
    def _register_generate_diagram(self):
        """Register the generate_diagram tool."""
        @self.mcp.tool()
        def generate_diagram(query: str, theme: Optional[str] = None) -> str:
            """Generate a Mermaid diagram from a text description.
            
            Args:
                query: Text description of the diagram to generate
                theme: Optional color theme to apply (default, dark, pastel, vibrant)
                
            Returns:
                str: Generated Mermaid diagram code with styling applied
            """
            if not query or not query.strip():
                error_msg = "Query cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Check if theme is valid
            if theme and theme not in self.style_manager.themes:
                logger.warning(f"Invalid theme '{theme}'. Using default theme.")
                theme = None
            
            # Check cache first
            cache_key = self._generate_cache_key("generate_diagram", query=query, theme=theme)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for generate_diagram with query: {query[:30]}...")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for generate_diagram with query: {query[:30]}...")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are an expert system designed to create Mermaid diagrams based on user queries. "
                       "Your task is to analyze the given input and generate a visual representation of the "
                       "concepts, relationships, or processes described. Return only the Mermaid diagram code "
                       "without any explanation. Include the Mermaid code fences in your response (```mermaid).",
                messages=[{"role": "user", "content": query}]
            )
            
            result = message.content[0].text
            
            # Extract Mermaid code from the response if it contains code fences
            if '```mermaid' in result and '```' in result.split('```mermaid', 1)[1]:
                result = result.split('```mermaid', 1)[1].split('```', 1)[0].strip()
            
            # Validate the generated diagram
            validation = MermaidValidator.validate(result)
            if not validation["is_valid"]:
                logger.warning(f"Generated diagram has validation issues: {validation['issues']}")
            
            # Apply styling
            styled_result = self.style_manager.add_styling_to_diagram(result, theme)
            
            # Store in cache
            self.cache.set(cache_key, styled_result)
            
            return styled_result
        
        return generate_diagram

    def _register_analyze_diagram(self):
        """Register the analyze_diagram tool."""
        @self.mcp.tool()
        def analyze_diagram(diagram: str) -> str:
            """Analyze a Mermaid diagram and provide insights.
            
            Args:
                diagram: Mermaid diagram code to analyze
                
            Returns:
                str: Analysis and insights about the diagram
            """
            if not diagram or not diagram.strip():
                error_msg = "Diagram cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Validate diagram first
            validation = MermaidValidator.validate(diagram)
            if not validation["is_valid"]:
                issues_str = "\n".join([f"- {issue}" for issue in validation["issues"]])
                error_msg = f"Invalid Mermaid diagram. Please fix the following issues:\n{issues_str}"
                logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Check cache first
            cache_key = self._generate_cache_key("analyze_diagram", diagram=diagram)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for analyze_diagram")
                return cached_result
                
            # Not in cache, make API call
            logger.info(f"Cache miss for analyze_diagram")
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are an expert in analyzing Mermaid diagrams. "
                       "Your task is to analyze the provided diagram code and provide insights about its "
                       "structure, clarity, and potential improvements.",
                messages=[{"role": "user", "content": f"Analyze this Mermaid diagram:\n\n{diagram}"}]
            )
            
            result = message.content[0].text
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return analyze_diagram

    def _register_modify_diagram(self):
        """Register the modify_diagram tool."""
        @self.mcp.tool()
        def modify_diagram(diagram: str, modification: str, theme: Optional[str] = None, keep_styling: bool = True) -> str:
            """Modify an existing Mermaid diagram based on instructions.
            
            Args:
                diagram: Original Mermaid diagram code
                modification: Description of desired modifications
                theme: Optional color theme to apply (default, dark, pastel, vibrant)
                keep_styling: Whether to preserve existing styling if present
                
            Returns:
                str: Modified Mermaid diagram code
            """
            if not diagram or not diagram.strip():
                error_msg = "Diagram cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not modification or not modification.strip():
                error_msg = "Modification instructions cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Check if theme is valid
            if theme and theme not in self.style_manager.themes:
                logger.warning(f"Invalid theme '{theme}'. Using default theme.")
                theme = None
            
            # Check cache first
            cache_key = self._generate_cache_key(
                "modify_diagram", 
                diagram=diagram, 
                modification=modification,
                theme=theme,
                keep_styling=keep_styling
            )
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for modify_diagram")
                return cached_result
            
            # Not in cache, make API call
            logger.info(f"Cache miss for modify_diagram")
            
            # Check if diagram already has styling
            has_styling = "style " in diagram or "classDef " in diagram or "%%{init:" in diagram
            
            # Strip styling if we're not keeping it
            if has_styling and not keep_styling:
                # Remove styling for flowcharts/graphs
                if "style " in diagram or "classDef " in diagram:
                    lines = diagram.strip().split('\n')
                    filtered_lines = []
                    for line in lines:
                        if not line.strip().startswith(("style ", "classDef ", "%%")):
                            filtered_lines.append(line)
                    diagram = '\n'.join(filtered_lines)
                
                # Remove styling for other diagram types
                if "%%{init:" in diagram:
                    lines = diagram.strip().split('\n')
                    filtered_lines = []
                    in_init_block = False
                    for line in lines:
                        if line.strip().startswith("%%{init:"):
                            in_init_block = True
                            continue
                        if in_init_block and "}}%%" in line:
                            in_init_block = False
                            continue
                        if not in_init_block:
                            filtered_lines.append(line)
                    diagram = '\n'.join(filtered_lines)
            
            # Make API call
            message = self._handle_api_call(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system="You are an expert in modifying Mermaid diagrams. "
                       "Your task is to take the provided Mermaid diagram code and modify it "
                       "according to the instructions. Return only the modified Mermaid diagram code "
                       "without any explanation. Preserve any existing styling unless instructed otherwise.",
                messages=[{
                    "role": "user",
                    "content": f"Modify this Mermaid diagram:\n\n{diagram}\n\nRequested changes:\n{modification}"
                }]
            )
            
            result = message.content[0].text
            
            # Extract Mermaid code from the response if it contains code fences
            if '```mermaid' in result and '```' in result.split('```mermaid', 1)[1]:
                result = result.split('```mermaid', 1)[1].split('```', 1)[0].strip()
            
            # Validate the modified diagram
            validation = MermaidValidator.validate(result)
            if not validation["is_valid"]:
                issues_str = "\n".join([f"- {issue}" for issue in validation["issues"]])
                error_msg = f"Modified diagram is invalid. Please fix the following issues:\n{issues_str}"
                logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Apply styling if needed
            has_styling_after_mod = "style " in result or "classDef " in result or "%%{init:" in result
            if not has_styling_after_mod and theme is not None:
                result = self.style_manager.add_styling_to_diagram(result, theme)
            
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return modify_diagram
        
    def _register_validate_diagram(self):
        """Register the validate_diagram tool."""
        @self.mcp.tool()
        def validate_diagram(diagram: str) -> Dict[str, Any]:
            """Validate Mermaid diagram syntax.
            
            Args:
                diagram: Mermaid diagram code to validate
                
            Returns:
                Dict with validation results including is_valid flag and issues list
            """
            if not diagram or not diagram.strip():
                raise ValueError("Diagram cannot be empty")
                
            # Perform validation
            validation_result = MermaidValidator.validate(diagram)
            
            return validation_result
        
        return validate_diagram
        
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
                },
                "styling": {
                    "default_theme": self.style_manager.default_theme,
                    "available_themes": list(self.style_manager.themes.keys())
                }
            }
        
        return get_status
        
    def _register_get_theme_info(self):
        """Register a tool to get theme information."""
        @self.mcp.tool()
        def get_theme_info(theme_name: Optional[str] = None) -> Dict[str, Any]:
            """Get information about available color themes.
            
            Args:
                theme_name: Optional name of a specific theme to get info for
                
            Returns:
                Dict containing theme information
            """
            if theme_name and theme_name not in self.style_manager.themes:
                raise ValueError(f"Theme '{theme_name}' not found. Available themes: {', '.join(self.style_manager.themes.keys())}")
                
            if theme_name:
                # Return info for just the requested theme
                return {
                    "name": theme_name,
                    "colors": self.style_manager.themes[theme_name],
                    "is_default": theme_name == self.style_manager.default_theme
                }
            else:
                # Return info for all themes
                return {
                    "default_theme": self.style_manager.default_theme,
                    "available_themes": list(self.style_manager.themes.keys()),
                    "themes": {
                        name: {
                            "colors": colors,
                            "is_default": name == self.style_manager.default_theme
                        } for name, colors in self.style_manager.themes.items()
                    }
                }
        
        return get_theme_info

    def _register_add_custom_theme(self):
        """Register a tool to add a custom theme."""
        @self.mcp.tool()
        def add_custom_theme(name: str, colors: Dict[str, str]) -> bool:
            """Add a new custom color theme.
            
            Args:
                name: Name for the new theme
                colors: Dictionary with color values (must include node_fill, node_border, node_text, edge, highlight, success, warning, error)
                
            Returns:
                bool: True if theme was added successfully
            """
            if not name or not name.strip():
                raise ValueError("Theme name cannot be empty")
                
            # Check if theme name is valid (alphanumeric with hyphens and underscores)
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                raise ValueError("Theme name must contain only letters, numbers, hyphens, and underscores")
                
            # Attempt to add the theme
            success = self.style_manager.add_custom_theme(name, colors)
            
            if not success:
                raise ValueError("Failed to add theme. Ensure all required colors are valid hex codes")
                
            return success
        
        return add_custom_theme
    
    def _register_remove_custom_theme(self):
        """Register a tool to remove a custom theme."""
        @self.mcp.tool()
        def remove_custom_theme(name: str) -> bool:
            """Remove a custom color theme.
            
            Args:
                name: Name of the theme to remove
                
            Returns:
                bool: True if theme was removed successfully
            """
            if not name or not name.strip():
                raise ValueError("Theme name cannot be empty")
                
            # Attempt to remove the theme
            success = self.style_manager.remove_custom_theme(name)
            
            if not success:
                raise ValueError(f"Failed to remove theme '{name}'. It may be a built-in theme or does not exist")
                
            return success
        
        return remove_custom_theme

    def _register_preview_diagram(self):
        """Register a tool to generate an SVG preview of a diagram."""
        @self.mcp.tool()
        def preview_diagram(diagram: str, theme: Optional[str] = None) -> str:
            """Generate an SVG preview of a Mermaid diagram.
            
            Args:
                diagram: Mermaid diagram code
                theme: Optional theme to apply (default, dark, pastel, vibrant, or custom)
                
            Returns:
                str: Base64-encoded SVG string
            """
            if not diagram or not diagram.strip():
                error_msg = "Diagram cannot be empty"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Apply styling if theme is specified
            if theme:
                diagram = self.style_manager.add_styling_to_diagram(diagram, theme)
            
            # Validate the diagram
            validation = MermaidValidator.validate(diagram)
            if not validation["is_valid"]:
                issues_str = "\n".join([f"- {issue}" for issue in validation["issues"]])
                error_msg = f"Invalid Mermaid diagram. Please fix the following issues:\n{issues_str}"
                logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Generate cache key based on diagram and theme
            cache_key = self._generate_cache_key("preview_diagram", diagram=diagram, theme=theme)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info("Cache hit for preview_diagram")
                return cached_result
                
            # Not in cache, generate SVG
            logger.info("Cache miss for preview_diagram, generating SVG")
            
            try:
                # Use Mermaid.ink service to render the diagram
                payload = {
                    "code": diagram,
                    "mermaid": {
                        "theme": "default"  # Base theme (styling already applied above)
                    }
                }
                
                # URL-safe base64 encode the payload
                payload_str = json.dumps(payload)
                payload_bytes = payload_str.encode("utf-8")
                payload_base64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8")
                
                # Request the SVG from mermaid.ink
                url = f"https://mermaid.ink/svg/{payload_base64}"
                response = requests.get(url, timeout=10)
                
                if response.status_code != 200:
                    raise ApiError(f"Failed to generate SVG: {response.text}")
                
                # Get the SVG content
                svg_content = response.text
                
                # Base64 encode for easy embedding
                svg_bytes = svg_content.encode("utf-8")
                svg_base64 = base64.b64encode(svg_bytes).decode("utf-8")
                
                # Cache the result
                self.cache.set(cache_key, svg_base64)
                
                return svg_base64
                
            except requests.RequestException as e:
                error_msg = f"Error generating SVG preview: {str(e)}"
                logger.error(error_msg)
                raise ApiError(error_msg)
        
        return preview_diagram

    def run(self):
        """Run the MCP server."""
        logger.info("Starting Mermaid MCP server")
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
    
    # Get default theme from environment or use default ("default")
    default_theme = os.environ.get("DEFAULT_THEME", "default")
    
    # Get custom themes path from environment or use default (None)
    custom_themes_path = os.environ.get("CUSTOM_THEMES_PATH")
    
    server = MermaidServer(cache_ttl=cache_ttl, calls_per_minute=calls_per_minute, default_theme=default_theme, custom_themes_path=custom_themes_path)
    server.run()

if __name__ == "__main__":
    main()
