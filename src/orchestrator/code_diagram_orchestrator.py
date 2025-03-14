"""
Code Diagram Orchestrator - MCP server that orchestrates between SOLID analyzer and Mermaid diagram generator.

NOTE: For a unified interface, consider using the MermaidOrchestratorServer from src.mermaid.mermaid_orchestrator.
"""

from mcp.server.fastmcp import FastMCP
import anthropic
import os
import logging
import hashlib
import json
import time
import threading
import sys
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('orchestrator')

# Add src directory to path to import other modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the individual servers (will be mocked when testing)
from solid.solid_server import SolidServer, SolidPrinciple
from mermaid.mermaid_server import MermaidServer

class OrchestratorError(Exception):
    """Base exception class for orchestrator errors."""
    pass

class TaskDecompositionError(OrchestratorError):
    """Exception raised when task decomposition fails."""
    pass

class WorkerError(OrchestratorError):
    """Exception raised when worker execution fails."""
    pass

class SynthesisError(OrchestratorError):
    """Exception raised when result synthesis fails."""
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
                
                if wait_time > 10:  # If wait time is too long, raise error
                    raise OrchestratorError(f"Rate limit exceeded. Would need to wait {wait_time:.1f} seconds.")
                
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
    
    def record_call(self) -> None:
        """Record that a call was made."""
        with self.lock:
            self.call_history.append(time.time())

class TaskScheduler:
    """Scheduler for managing task dependencies and execution order."""
    
    def create_plan(self, assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create an execution plan based on task dependencies.
        
        Args:
            assignments: List of worker assignments
            
        Returns:
            Ordered list of assignments to execute
        """
        # First, assign IDs to tasks if they don't have them
        for i, assignment in enumerate(assignments):
            if 'id' not in assignment:
                assignment['id'] = f"task_{i}"
        
        # Build dependency graph
        dependency_graph = {}
        for assignment in assignments:
            task_id = assignment['id']
            dependencies = assignment.get('dependencies', [])
            dependency_graph[task_id] = dependencies
        
        # Topological sort to order tasks
        visited = set()
        temp = set()
        order = []
        
        def visit(node):
            if node in temp:
                raise TaskDecompositionError(f"Circular dependency detected involving task {node}")
            if node not in visited:
                temp.add(node)
                for dependency in dependency_graph.get(node, []):
                    visit(dependency)
                temp.remove(node)
                visited.add(node)
                order.append(node)
        
        for node in dependency_graph:
            if node not in visited:
                visit(node)
        
        # Map back to assignments
        task_map = {a['id']: a for a in assignments}
        return [task_map[task_id] for task_id in order]

    def order_results(self, worker_results: Dict[str, Any]) -> List[Any]:
        """
        Order results based on task dependencies.
        
        Args:
            worker_results: Dict mapping task IDs to results
            
        Returns:
            Ordered list of results
        """
        # Simple implementation just returns values in the order they appear in the dict
        # This can be enhanced with more sophisticated ordering logic if needed
        return list(worker_results.values())

class ResultSynthesizer:
    """Combines results from multiple workers into a final result."""
    
    def combine_results(self, results: List[Any], orchestrator_model: Any) -> Any:
        """
        Combine results from multiple workers.
        
        Args:
            results: List of results to combine
            orchestrator_model: LLM for orchestration
            
        Returns:
            Combined final result
        """
        # This is a placeholder - in a real implementation, you'd have more
        # sophisticated logic for combining heterogeneous results
        if not results:
            return None
            
        # If there's only one result, return it directly
        if len(results) == 1:
            return results[0]
            
        # For multiple results, we'd typically use the orchestrator_model to combine them
        return {
            "combined_results": results,
            "type": "multi_result"
        }

class CodeDiagramOrchestrator:
    """Orchestrator to coordinate between SOLID analysis and Mermaid diagram generation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl: int = 3600,
        calls_per_minute: int = 15
    ):
        """
        Initialize the orchestrator.
        
        Args:
            api_key: Anthropic API key
            cache_ttl: Cache time-to-live in seconds
            calls_per_minute: API rate limit
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        # Initialize worker servers
        logger.info("Initializing worker servers")
        self.solid_server = SolidServer(api_key=self.api_key)
        self.mermaid_server = MermaidServer(api_key=self.api_key)
        
        # Initialize orchestrator components
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.mcp = FastMCP("code-diagram-orchestrator")
        self.cache = Cache(ttl_seconds=cache_ttl)
        self.rate_limiter = RateLimiter(calls_per_minute=calls_per_minute)
        
        # Initialize task management components
        self.scheduler = TaskScheduler()
        self.synthesizer = ResultSynthesizer()
        
        # Initialize workers registry
        self.workers = {
            "solid_analyzer": self.solid_server,
            "mermaid_generator": self.mermaid_server
        }
        
        # Set up MCP tools
        self.setup_tools()
    
    def setup_tools(self):
        """Set up MCP tools."""
        self.analyze_and_visualize = self._register_analyze_and_visualize()
        self.generate_class_diagram = self._register_generate_class_diagram()
        self.create_documentation = self._register_create_documentation()
        self.clear_cache = self._register_clear_cache()
    
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
    
    def _handle_api_call(self, func: callable, *args, **kwargs) -> Any:
        """
        Handle API calls with error handling, rate limiting, and logging.
        
        Args:
            func: The API function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: The result of the API call
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
        except Exception as e:
            error_msg = f"API call failed: {str(e)}"
            logger.error(error_msg)
            raise OrchestratorError(error_msg) from e
    
    def decompose_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decompose task into worker assignments.
        
        Args:
            task: Complex task to decompose
            
        Returns:
            List of worker assignments
        """
        try:
            # For simple tasks, we have predefined decomposition logic
            if task['type'] == 'analyze_and_visualize':
                return [
                    {
                        'id': 'analyze',
                        'worker_type': 'solid_analyzer',
                        'subtask': {
                            'action': 'analyze_code',
                            'code': task['code'],
                            'principles': task.get('principles', None)
                        },
                        'dependencies': []
                    },
                    {
                        'id': 'visualize',
                        'worker_type': 'mermaid_generator',
                        'subtask': {
                            'action': 'generate_diagram',
                            'code_context': task['code'],
                            'analysis_dependency': 'analyze'
                        },
                        'dependencies': ['analyze']
                    }
                ]
            elif task['type'] == 'generate_class_diagram':
                return [
                    {
                        'id': 'generate_diagram',
                        'worker_type': 'mermaid_generator',
                        'subtask': {
                            'action': 'generate_diagram',
                            'query': f"Create a class diagram for this code:\n\n{task['code']}"
                        },
                        'dependencies': []
                    }
                ]
            elif task['type'] == 'create_documentation':
                return [
                    {
                        'id': 'analyze',
                        'worker_type': 'solid_analyzer',
                        'subtask': {
                            'action': 'analyze_code',
                            'code': task['code']
                        },
                        'dependencies': []
                    },
                    {
                        'id': 'generate_diagram',
                        'worker_type': 'mermaid_generator',
                        'subtask': {
                            'action': 'generate_diagram',
                            'query': f"Create a class diagram for this code:\n\n{task['code']}"
                        },
                        'dependencies': []
                    }
                ]
            else:
                # For complex or unknown tasks, we could use LLM-based decomposition
                # This is a placeholder - in a real implementation, you'd use the orchestrator_llm
                raise TaskDecompositionError(f"Unknown task type: {task['type']}")
                
        except Exception as e:
            logger.error(f"Task decomposition failed: {str(e)}")
            raise TaskDecompositionError(f"Failed to decompose task: {str(e)}")
    
    def assign_workers(self, assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assign tasks to appropriate workers.
        
        Args:
            assignments: List of worker assignments
            
        Returns:
            Dict mapping assignment IDs to workers
        """
        try:
            # Create execution plan
            execution_plan = self.scheduler.create_plan(assignments)
            
            # Assign workers
            worker_assignments = {}
            for assignment in execution_plan:
                worker_type = assignment['worker_type']
                if worker_type not in self.workers:
                    raise WorkerError(f"No worker for type {worker_type}")
                    
                worker = self.workers[worker_type]
                worker_assignments[assignment['id']] = {
                    'worker': worker,
                    'assignment': assignment
                }
                
            return worker_assignments
        except Exception as e:
            logger.error(f"Worker assignment failed: {str(e)}")
            raise WorkerError(f"Failed to assign workers: {str(e)}")
    
    def execute_worker_tasks(self, worker_assignments: Dict[str, Any], results_so_far: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute worker tasks and collect results.
        
        Args:
            worker_assignments: Dict mapping assignment IDs to workers
            results_so_far: Results from previously executed tasks
            
        Returns:
            Dict mapping assignment IDs to results
        """
        if results_so_far is None:
            results_so_far = {}
        
        worker_results = results_so_far.copy()
        
        for assignment_id, info in worker_assignments.items():
            if assignment_id in worker_results:
                # Skip already executed tasks
                continue
                
            worker = info['worker']
            assignment = info['assignment']
            subtask = assignment['subtask']
            
            # Check if all dependencies are satisfied
            dependencies = assignment.get('dependencies', [])
            if not all(dep in worker_results for dep in dependencies):
                logger.warning(f"Skipping task {assignment_id} because dependencies are not satisfied")
                continue
            
            # Execute the task based on the worker type and action
            try:
                if assignment['worker_type'] == 'solid_analyzer':
                    if subtask['action'] == 'analyze_code':
                        principles = subtask.get('principles')
                        result = worker.analyze_code(subtask['code'], principles)
                        worker_results[assignment_id] = result
                elif assignment['worker_type'] == 'mermaid_generator':
                    if subtask['action'] == 'generate_diagram':
                        # If there's an analysis dependency, incorporate it into the query
                        if 'analysis_dependency' in subtask and subtask['analysis_dependency'] in worker_results:
                            analysis = worker_results[subtask['analysis_dependency']]
                            query = f"Create a class diagram based on this code and analysis:\n\nCode:\n{subtask['code_context']}\n\nAnalysis:\n{analysis}"
                            result = worker.generate_diagram(query)
                        else:
                            result = worker.generate_diagram(subtask['query'])
                        worker_results[assignment_id] = result
                else:
                    raise WorkerError(f"Unknown worker type: {assignment['worker_type']}")
            except Exception as e:
                logger.error(f"Worker task execution failed: {str(e)}")
                raise WorkerError(f"Failed to execute task {assignment_id}: {str(e)}")
        
        return worker_results
    
    def synthesize_results(self, worker_results: Dict[str, Any], task: Dict[str, Any]) -> Any:
        """
        Synthesize results from multiple workers.
        
        Args:
            worker_results: Dict mapping assignment IDs to results
            task: The original task
            
        Returns:
            Synthesized final result
        """
        try:
            # Order results by dependencies
            ordered_results = self.scheduler.order_results(worker_results)
            
            # Synthesize based on task type
            if task['type'] == 'analyze_and_visualize':
                # Return a combined result with both analysis and diagram
                if 'analyze' in worker_results and 'visualize' in worker_results:
                    return {
                        'analysis': worker_results['analyze'],
                        'diagram': worker_results['visualize']
                    }
            elif task['type'] == 'generate_class_diagram':
                # Return just the diagram
                if 'generate_diagram' in worker_results:
                    return worker_results['generate_diagram']
            elif task['type'] == 'create_documentation':
                # Combine analysis and diagram into documentation
                analysis = worker_results.get('analyze', '')
                diagram = worker_results.get('generate_diagram', '')
                
                # Use the orchestrator to combine them
                message = self._handle_api_call(
                    self.client.messages.create,
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8192,
                    temperature=0,
                    system="You are an expert technical writer. Create comprehensive documentation using the provided code analysis and diagram.",
                    messages=[{
                        "role": "user",
                        "content": f"Create documentation for this code:\n\nAnalysis:\n{analysis}\n\nClass Diagram:\n{diagram}\n\nCode:\n{task['code']}"
                    }]
                )
                
                return message.content[0].text
            
            # Fall back to general synthesis method
            return self.synthesizer.combine_results(ordered_results, self.client)
            
        except Exception as e:
            logger.error(f"Result synthesis failed: {str(e)}")
            raise SynthesisError(f"Failed to synthesize results: {str(e)}")
    
    def _register_analyze_and_visualize(self):
        """Register the analyze_and_visualize tool."""
        @self.mcp.tool()
        def analyze_and_visualize(code: str, principles: Optional[List[str]] = None) -> Dict[str, str]:
            """Analyze code against SOLID principles and generate a diagram from the results.
            
            Args:
                code: Code to analyze
                principles: Optional list of specific principles to check
                
            Returns:
                Dict containing analysis and diagram
            """
            if not code or not code.strip():
                raise ValueError("Code cannot be empty")
            
            # Check cache first
            cache_key = self._generate_cache_key("analyze_and_visualize", code=code, principles=principles)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for analyze_and_visualize")
                return cached_result
            
            # Define the task
            task = {
                'type': 'analyze_and_visualize',
                'code': code,
                'principles': principles
            }
            
            # Decompose task into worker assignments
            assignments = self.decompose_task(task)
            
            # Assign workers to tasks
            worker_assignments = self.assign_workers(assignments)
            
            # Execute worker tasks
            worker_results = self.execute_worker_tasks(worker_assignments)
            
            # Synthesize results
            result = self.synthesize_results(worker_results, task)
            
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return analyze_and_visualize
    
    def _register_generate_class_diagram(self):
        """Register the generate_class_diagram tool."""
        @self.mcp.tool()
        def generate_class_diagram(code: str) -> str:
            """Generate a class diagram from code.
            
            Args:
                code: Code to generate diagram from
                
            Returns:
                str: Mermaid diagram code
            """
            if not code or not code.strip():
                raise ValueError("Code cannot be empty")
            
            # Check cache first
            cache_key = self._generate_cache_key("generate_class_diagram", code=code)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for generate_class_diagram")
                return cached_result
            
            # Define the task
            task = {
                'type': 'generate_class_diagram',
                'code': code
            }
            
            # Decompose task into worker assignments
            assignments = self.decompose_task(task)
            
            # Assign workers to tasks
            worker_assignments = self.assign_workers(assignments)
            
            # Execute worker tasks
            worker_results = self.execute_worker_tasks(worker_assignments)
            
            # Synthesize results
            result = self.synthesize_results(worker_results, task)
            
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return generate_class_diagram
    
    def _register_create_documentation(self):
        """Register the create_documentation tool."""
        @self.mcp.tool()
        def create_documentation(code: str) -> str:
            """Create comprehensive documentation for code with analysis and diagrams.
            
            Args:
                code: Code to document
                
            Returns:
                str: Markdown documentation
            """
            if not code or not code.strip():
                raise ValueError("Code cannot be empty")
            
            # Check cache first
            cache_key = self._generate_cache_key("create_documentation", code=code)
            hit, cached_result = self.cache.get(cache_key)
            
            if hit:
                logger.info(f"Cache hit for create_documentation")
                return cached_result
            
            # Define the task
            task = {
                'type': 'create_documentation',
                'code': code
            }
            
            # Decompose task into worker assignments
            assignments = self.decompose_task(task)
            
            # Assign workers to tasks
            worker_assignments = self.assign_workers(assignments)
            
            # Execute worker tasks
            worker_results = self.execute_worker_tasks(worker_assignments)
            
            # Synthesize results
            result = self.synthesize_results(worker_results, task)
            
            # Store in cache
            self.cache.set(cache_key, result)
            
            return result
        
        return create_documentation
    
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
    
    def run(self):
        """Run the MCP server."""
        logger.info("Starting Code Diagram Orchestrator MCP server")
        self.mcp.run()

def main():
    """Main entry point."""
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY environment variable not set.")
        logger.warning("The server will fail to process requests without a valid API key.")
    
    server = CodeDiagramOrchestrator()
    server.run()

if __name__ == "__main__":
    main() 