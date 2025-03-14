#!/usr/bin/env python
"""
MCP Integrated System Deployment

This script automates the deployment and integration of all MCP servers with the MCP Router.
It provides a comprehensive, one-command solution for setting up the entire MCP ecosystem.
"""

import os
import sys
import argparse
import logging
import json
import yaml
import subprocess
import time
import shutil
import tempfile
import signal
import atexit
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import threading
import socket
from contextlib import closing
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deploy_integrated_system.log')
    ]
)
logger = logging.getLogger('deploy_system')

# Global variables
processes = []
stop_event = threading.Event()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Deploy integrated MCP system")
    
    parser.add_argument(
        "--router-only",
        action="store_true",
        help="Deploy only the MCP Router"
    )
    
    parser.add_argument(
        "--servers",
        type=str,
        nargs="+",
        choices=["orchestrator", "project-orchestrator", "prompts", "memory", "filesystem", "all"],
        default=["all"],
        help="Specific servers to deploy (default: all)"
    )
    
    parser.add_argument(
        "--router-port",
        type=int,
        default=3000,
        help="Port for the MCP Router"
    )
    
    parser.add_argument(
        "--server-ports",
        type=str,
        default="orchestrator=8001,project-orchestrator=8002,prompts=8003,memory=8004,filesystem=8005",
        help="Comma-separated list of server-port pairs (e.g., 'orchestrator=8001,prompts=8003')"
    )
    
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Run in development mode with hot-reloading"
    )
    
    parser.add_argument(
        "--detached",
        action="store_true",
        help="Run in detached mode (background)"
    )
    
    parser.add_argument(
        "--log-dir",
        type=str,
        default="./logs",
        help="Directory for log files"
    )
    
    parser.add_argument(
        "--config-dir",
        type=str,
        default="./config",
        help="Directory for configuration files"
    )
    
    parser.add_argument(
        "--generate-configs",
        action="store_true",
        help="Generate configuration files"
    )
    
    parser.add_argument(
        "--integration-test",
        action="store_true",
        help="Run integration tests after deployment"
    )
    
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Use Docker for deployment"
    )
    
    parser.add_argument(
        "--docker-compose-file",
        type=str,
        default="./docker-compose.yml",
        help="Path to docker-compose.yml file"
    )
    
    parser.add_argument(
        "--environment",
        type=str,
        choices=["development", "staging", "production"],
        default="development",
        help="Deployment environment"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for server startup"
    )
    
    parser.add_argument(
        "--healthcheck",
        action="store_true",
        help="Run health checks after deployment"
    )
    
    return parser.parse_args()

def generate_config_files(args):
    """
    Generate configuration files for MCP servers and router.
    
    Args:
        args: Command-line arguments
    """
    logger.info("Generating configuration files...")
    
    # Create config directory if it doesn't exist
    config_dir = Path(args.config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse server ports
    server_ports = {}
    for pair in args.server_ports.split(','):
        if '=' in pair:
            server, port = pair.split('=')
            server_ports[server] = int(port)
    
    # Generate router configuration
    router_config = {
        "server": {
            "port": args.router_port,
            "host": "0.0.0.0",
            "environment": args.environment
        },
        "logging": {
            "level": "debug" if args.verbose else "info",
            "file": str(Path(args.log_dir) / "router.log")
        },
        "capabilities": {
            "healthCheckInterval": 30,
            "enableDiscovery": True
        },
        "security": {
            "enabled": args.environment == "production",
            "jwtSecret": "development-secret-change-in-production",
            "tokenExpiration": "1h"
        }
    }
    
    router_config_path = config_dir / "router.json"
    with open(router_config_path, 'w') as f:
        json.dump(router_config, f, indent=2)
    
    logger.info(f"Generated router configuration: {router_config_path}")
    
    # Generate server configurations
    server_configs = {
        "orchestrator": {
            "server_id": "code-diagram-orchestrator",
            "server_name": "Code Diagram Orchestrator",
            "server_description": "MCP server for code analysis, visualization, and documentation",
            "server_host": "0.0.0.0",
            "server_port": server_ports.get("orchestrator", 8001),
            "router_url": f"http://localhost:{args.router_port}",
            "log_level": "DEBUG" if args.verbose else "INFO",
            "log_file": str(Path(args.log_dir) / "orchestrator.log"),
            "api_key": os.environ.get("ANTHROPIC_API_KEY", "")
        },
        "project-orchestrator": {
            "server_id": "project-orchestrator",
            "server_name": "Project Orchestrator",
            "server_description": "MCP server for project orchestration and template application",
            "server_host": "0.0.0.0",
            "server_port": server_ports.get("project-orchestrator", 8002),
            "router_url": f"http://localhost:{args.router_port}",
            "log_level": "DEBUG" if args.verbose else "INFO",
            "log_file": str(Path(args.log_dir) / "project-orchestrator.log"),
            "projects_dir": "./projects",
            "templates_file": "./project_templates.json",
            "component_templates_file": "./component_templates.json"
        },
        "prompts": {
            "server_id": "prompt-manager",
            "server_name": "Prompt Manager",
            "server_description": "MCP server for prompt management and template application",
            "server_host": "0.0.0.0",
            "server_port": server_ports.get("prompts", 8003),
            "router_url": f"http://localhost:{args.router_port}",
            "log_level": "DEBUG" if args.verbose else "INFO",
            "log_file": str(Path(args.log_dir) / "prompts.log"),
            "prompts_dir": "./prompts",
            "backup_dir": "./backups",
            "enable_versioning": True
        },
        "memory": {
            "server_id": "memory-server",
            "server_name": "Memory Server",
            "server_description": "MCP server for knowledge graph management",
            "server_host": "0.0.0.0",
            "server_port": server_ports.get("memory", 8004),
            "router_url": f"http://localhost:{args.router_port}",
            "log_level": "DEBUG" if args.verbose else "INFO",
            "log_file": str(Path(args.log_dir) / "memory.log"),
            "storage_type": "memory",
            "embedding_enabled": False
        },
        "filesystem": {
            "server_id": "filesystem-server",
            "server_name": "Filesystem Server",
            "server_description": "MCP server for file system operations",
            "server_host": "0.0.0.0",
            "server_port": server_ports.get("filesystem", 8005),
            "router_url": f"http://localhost:{args.router_port}",
            "log_level": "DEBUG" if args.verbose else "INFO",
            "log_file": str(Path(args.log_dir) / "filesystem.log"),
            "allowed_directories": [str(Path.home() / "projects")],
            "allow_write_operations": True
        }
    }
    
    for server_type, config in server_configs.items():
        config_path = config_dir / f"{server_type}.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Generated {server_type} configuration: {config_path}")
    
    # Generate docker-compose.yml if using Docker
    if args.docker:
        generate_docker_compose(args, server_ports)

def generate_docker_compose(args, server_ports):
    """
    Generate docker-compose.yml file for Docker deployment.
    
    Args:
        args: Command-line arguments
        server_ports: Dictionary of server ports
    """
    docker_compose = {
        "version": "3.8",
        "services": {
            "router": {
                "build": {
                    "context": "/home/sparrow/projects/mcp-router",
                    "dockerfile": "Dockerfile"
                },
                "ports": [f"{args.router_port}:{args.router_port}"],
                "volumes": [
                    f"{args.config_dir}:/app/config",
                    f"{args.log_dir}:/app/logs"
                ],
                "environment": [
                    f"NODE_ENV={args.environment}",
                    f"PORT={args.router_port}",
                    "CONFIG_FILE=/app/config/router.json"
                ],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": f"curl --fail http://localhost:{args.router_port}/api/health || exit 1",
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                }
            }
        },
        "networks": {
            "mcp-network": {
                "driver": "bridge"
            }
        }
    }
    
    # Add server configurations
    for server_type in ["orchestrator", "project-orchestrator", "prompts", "memory", "filesystem"]:
        if "all" in args.servers or server_type in args.servers:
            port = server_ports.get(server_type, 8000)
            
            server_config = {
                "build": {
                    "context": f"/home/sparrow/projects/mcp-{'servers' if server_type == 'orchestrator' else server_type}",
                    "dockerfile": "Dockerfile"
                },
                "ports": [f"{port}:{port}"],
                "volumes": [
                    f"{args.config_dir}:/app/config",
                    f"{args.log_dir}:/app/logs"
                ],
                "environment": [
                    f"MCP_CONFIG_FILE=/app/config/{server_type}.json",
                    f"MCP_SERVER_PORT={port}",
                    f"MCP_ROUTER_URL=http://router:{args.router_port}"
                ],
                "restart": "unless-stopped",
                "depends_on": ["router"],
                "networks": ["mcp-network"]
            }
            
            # Add API key for orchestrator
            if server_type == "orchestrator":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if api_key:
                    server_config["environment"].append(f"ANTHROPIC_API_KEY={api_key}")
            
            docker_compose["services"][server_type] = server_config
    
    # Write docker-compose.yml
    docker_compose_path = Path(args.docker_compose_file)
    with open(docker_compose_path, 'w') as f:
        yaml.dump(docker_compose, f)
    
    logger.info(f"Generated Docker Compose file: {docker_compose_path}")

def is_port_available(port):
    """
    Check if a port is available.
    
    Args:
        port: Port number to check
    
    Returns:
        True if port is available, False otherwise
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        return s.connect_ex(('localhost', port)) != 0

def wait_for_server(url, timeout=60):
    """
    Wait for a server to become available.
    
    Args:
        url: URL to check
        timeout: Timeout in seconds
    
    Returns:
        True if server is available, False otherwise
    """
    import requests
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        
        time.sleep(1)
    
    return False

def run_docker_deployment(args):
    """
    Run Docker deployment using docker-compose.
    
    Args:
        args: Command-line arguments
    
    Returns:
        True if deployment successful, False otherwise
    """
    logger.info("Starting Docker deployment...")
    
    # Build and start containers
    cmd = ["docker-compose", "-f", args.docker_compose_file, "up"]
    
    if args.detached:
        cmd.append("-d")
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(cmd)
        processes.append(process)
        
        if not args.detached:
            process.wait()
        else:
            # Wait for router to become available
            router_url = f"http://localhost:{args.router_port}/api/health"
            if wait_for_server(router_url, args.timeout):
                logger.info(f"Router is available at {router_url}")
            else:
                logger.error(f"Router did not become available within {args.timeout} seconds")
                return False
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker deployment failed: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        return False

def run_local_deployment(args):
    """
    Run local deployment of MCP servers and router.
    
    Args:
        args: Command-line arguments
    
    Returns:
        True if deployment successful, False otherwise
    """
    logger.info("Starting local deployment...")
    
    # Create log directory if it doesn't exist
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse server ports
    server_ports = {}
    for pair in args.server_ports.split(','):
        if '=' in pair:
            server, port = pair.split('=')
            server_ports[server] = int(port)
    
    # Check port availability
    if not is_port_available(args.router_port):
        logger.error(f"Router port {args.router_port} is already in use")
        return False
    
    for server, port in server_ports.items():
        if "all" in args.servers or server in args.servers:
            if not is_port_available(port):
                logger.error(f"Server port {port} for {server} is already in use")
                return False
    
    # Start router
    if not args.router_only and not start_router(args):
        return False
    
    # Start servers
    if not args.router_only:
        for server_type in ["orchestrator", "project-orchestrator", "prompts", "memory", "filesystem"]:
            if "all" in args.servers or server_type in args.servers:
                if not start_server(server_type, args, server_ports.get(server_type, 8000)):
                    logger.error(f"Failed to start {server_type} server")
                    return False
    
    # Wait for servers to register with router
    if not args.router_only:
        if not wait_for_server(f"http://localhost:{args.router_port}/api/mcp/capabilities/servers", args.timeout):
            logger.error(f"Servers did not register with router within {args.timeout} seconds")
            return False
    
    # Run health checks if enabled
    if args.healthcheck:
        run_health_checks(args)
    
    # Run integration tests if enabled
    if args.integration_test:
        run_integration_tests(args)
    
    # In non-detached mode, wait for interrupt
    if not args.detached:
        try:
            logger.info("Deployment successful. Press Ctrl+C to stop...")
            while not stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deployment interrupted by user")
    
    return True

def start_router(args):
    """
    Start the MCP Router.
    
    Args:
        args: Command-line arguments
    
    Returns:
        True if router started successfully, False otherwise
    """
    logger.info("Starting MCP Router...")
    
    # Command to start router
    cmd = ["npm", "run", "start:dev" if args.dev_mode else "start"]
    
    # Environment variables
    env = os.environ.copy()
    env["PORT"] = str(args.router_port)
    env["NODE_ENV"] = args.environment
    env["CONFIG_FILE"] = str(Path(args.config_dir) / "router.json")
    
    # Start router process
    try:
        log_file = open(Path(args.log_dir) / "router.log", "w")
        
        process = subprocess.Popen(
            cmd,
            cwd="/home/sparrow/projects/mcp-router",
            env=env,
            stdout=log_file if args.detached else subprocess.PIPE,
            stderr=log_file if args.detached else subprocess.PIPE,
            universal_newlines=True
        )
        
        processes.append(process)
        
        # Wait for router to start
        router_url = f"http://localhost:{args.router_port}/api/health"
        if wait_for_server(router_url, args.timeout):
            logger.info(f"Router started successfully on port {args.router_port}")
            return True
        else:
            logger.error(f"Router did not start within {args.timeout} seconds")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to start router: {e}")
        return False

def start_server(server_type, args, port):
    """
    Start an MCP server.
    
    Args:
        server_type: Type of server to start
        args: Command-line arguments
        port: Port for the server
    
    Returns:
        True if server started successfully, False otherwise
    """
    logger.info(f"Starting {server_type} server on port {port}...")
    
    # Determine server directory and command
    if server_type == "orchestrator":
        server_dir = "/home/sparrow/projects/mcp-servers/src/orchestrator"
        cmd = ["python", "enhanced_orchestrator.py"]
    elif server_type == "project-orchestrator":
        server_dir = "/home/sparrow/projects/mcp-project-orchestrator/src/mcp_project_orchestrator"
        cmd = ["python", "-m", "enhanced_orchestrator"]
    elif server_type == "prompts":
        server_dir = "/home/sparrow/projects/mcp-prompts/src"
        cmd = ["python", "-m", "prompts.server"]
    elif server_type == "memory":
        server_dir = "/home/sparrow/projects/mcp-servers/src/memory"
        cmd = ["python", "memory_server.py"]
    elif server_type == "filesystem":
        server_dir = "/home/sparrow/projects/mcp-servers/src/filesystem"
        cmd = ["python", "filesystem_server.py"]
    else:
        logger.error(f"Unknown server type: {server_type}")
        return False
    
    # Add arguments
    cmd.extend([
        "--server-id", f"{server_type}-server",
        "--router-url", f"http://localhost:{args.router_port}"
    ])
    
    # Environment variables
    env = os.environ.copy()
    env["MCP_SERVER_PORT"] = str(port)
    env["MCP_CONFIG_FILE"] = str(Path(args.config_dir) / f"{server_type}.json")
    env["MCP_LOG_LEVEL"] = "DEBUG" if args.verbose else "INFO"
    env["MCP_LOG_FILE"] = str(Path(args.log_dir) / f"{server_type}.log")
    
    # Start server process
    try:
        log_file = open(Path(args.log_dir) / f"{server_type}.log", "w")
        
        process = subprocess.Popen(
            cmd,
            cwd=server_dir,
            env=env,
            stdout=log_file if args.detached else subprocess.PIPE,
            stderr=log_file if args.detached else subprocess.PIPE,
            universal_newlines=True
        )
        
        processes.append(process)
        
        # Wait for server to start
        server_url = f"http://localhost:{port}/health"
        if wait_for_server(server_url, args.timeout):
            logger.info(f"{server_type} server started successfully on port {port}")
            return True
        else:
            logger.error(f"{server_type} server did not start within {args.timeout} seconds")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to start {server_type} server: {e}")
        return False

def run_health_checks(args):
    """
    Run health checks on all deployed servers.
    
    Args:
        args: Command-line arguments
    """
    logger.info("Running health checks...")
    
    # Check router health
    router_url = f"http://localhost:{args.router_port}/api/health"
    if wait_for_server(router_url, 5):
        logger.info("Router health check: PASSED")
    else:
        logger.error("Router health check: FAILED")
    
    # Parse server ports
    server_ports = {}
    for pair in args.server_ports.split(','):
        if '=' in pair:
            server, port = pair.split('=')
            server_ports[server] = int(port)
    
    # Check server health
    if not args.router_only:
        for server_type in ["orchestrator", "project-orchestrator", "prompts", "memory", "filesystem"]:
            if "all" in args.servers or server_type in args.servers:
                port = server_ports.get(server_type, 8000)
                server_url = f"http://localhost:{port}/health"
                
                if wait_for_server(server_url, 5):
                    logger.info(f"{server_type} server health check: PASSED")
                else:
                    logger.error(f"{server_type} server health check: FAILED")
    
    # Check server registration with router
    import requests
    try:
        response = requests.get(f"http://localhost:{args.router_port}/api/mcp/capabilities/servers", timeout=5)
        if response.status_code == 200:
            servers = response.json().get("servers", [])
            logger.info(f"Found {len(servers)} servers registered with router")
            
            # Log server details
            for server in servers:
                logger.info(f"  - {server['id']}: {server.get('health', 'unknown')}")
        else:
            logger.error(f"Failed to get server list: HTTP {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error checking server registration: {e}")

def run_integration_tests(args):
    """
    Run integration tests.
    
    Args:
        args: Command-line arguments
    """
    logger.info("Running integration tests...")
    
    # Check if integration test script exists
    test_script = Path("/home/sparrow/projects/mcp-router/tests/run_integration_tests.py")
    if not test_script.exists():
        logger.error(f"Integration test script not found: {test_script}")
        return
    
    # Run integration tests
    cmd = [
        "python",
        str(test_script),
        "--skip-router",
        "--skip-servers",
        "--wait-time", "5",
        "--show-output"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd="/home/sparrow/projects/mcp-router",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("Integration tests passed")
            logger.debug(stdout)
        else:
            logger.error("Integration tests failed")
            logger.error(stderr)
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to run integration tests: {e}")

def shutdown_deployment():
    """Shutdown all processes on exit."""
    logger.info("Shutting down deployment...")
    
    for process in processes:
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logger.error(f"Error terminating process: {e}")

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Register shutdown handler
    atexit.register(shutdown_deployment)
    
    # Handle interruption
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        stop_event.set()
        shutdown_deployment()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Generate configuration files if needed
    if args.generate_configs:
        generate_config_files(args)
    
    # Run deployment
    if args.docker:
        success = run_docker_deployment(args)
    else:
        success = run_local_deployment(args)
    
    # Exit with appropriate status
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
