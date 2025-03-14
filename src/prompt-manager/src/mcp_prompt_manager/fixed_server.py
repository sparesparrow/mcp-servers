"""
Updated serve function for the prompt_manager_server.py file that properly initializes InitializationOptions.
"""

async def serve():
    """Run the prompt manager MCP server."""
    # Load configuration
    config.from_env()
    config.load()
    
    # Configure logging based on config
    logging.basicConfig(level=getattr(logging, config.log_level))
    logger.setLevel(getattr(logging, config.log_level))
    
    logger.info(f"Starting Prompt Manager MCP Server [{config.server_name}]")
    
    # Load templates
    template_manager.load_templates()
    logger.info(f"Loaded {len(template_manager._templates)} templates")
    
    # Create server instance
    server = Server(config.server_name)

    # Register handlers
    server.list_prompts()(handle_list_prompts)
    server.get_prompt()(handle_get_prompt)
    server.list_resources()(handle_list_resources)
    server.read_resource()(handle_read_resource)
    server.list_tools()(handle_list_tools)
    server.call_tool()(handle_call_tool)

    # Run the server with appropriate error handling
    try:
        # Create initialization options with required fields
        options = InitializationOptions(
            server_name=config.server_name,
            server_version="0.1.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
        )
        await server.stdio_serve(options)
    except Exception as e:
        logger.error(f"Error running server: {e}")
        raise