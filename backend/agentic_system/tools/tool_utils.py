from pathlib import Path
import asyncio

from mcp import ClientSession, stdio_client, StdioServerParameters
import dspy


def mcp_tool_with_prefix(mcp, prefix):
    """
    Returns a decorator generator that prepends a prefix to all MCP tool names.
    Use as: mcp.tool = mcp_tool_with_prefix(mcp, "PUBCHEM")
    """
    _orig_tool = mcp.tool

    def tool_with_prefix(*dargs, **dkwargs):
        # Case 1: bare usage -> @mcp.tool
        if dargs and callable(dargs[0]) and not dkwargs:
            fn = dargs[0]
            return _orig_tool(name=f"{prefix}__{fn.__name__}")(fn)

        # Case 2: parentheses usage -> @mcp.tool(...)
        def decorator(fn):
            given_name = dkwargs.get("name", fn.__name__)
            new_kwargs = dkwargs.copy()
            new_kwargs["name"] = f"{prefix}__{given_name}"
            return _orig_tool(**new_kwargs)(fn)

        return decorator

    return tool_with_prefix


def get_mcp_tools(path_to_mcp_server: str):
    """synchronous version"""
    return asyncio.run(get_mcp_tools_async(path_to_mcp_server=Path(path_to_mcp_server)))


async def get_mcp_tools_async(path_to_mcp_server: Path):
    """Returns List[dspy.Tool] of synchronous versions of MCP server tool for given path"""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", str(path_to_mcp_server)],
        env=None,
    )

    # First, just get the tool definitions
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    # Now create sync wrappers that will create new sessions
    dspy_tools = []
    for tool in tools.tools:

        def make_sync_func(tool_name, server_params):
            def sync_func(**kwargs):
                # Create a new event loop for this call
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        call_mcp_tool(server_params, tool_name, kwargs)
                    )
                finally:
                    loop.close()

            sync_func.__name__ = tool_name
            return sync_func

        sync_func = make_sync_func(tool.name, server_params)
        sync_tool = dspy.Tool(
            func=sync_func,
            name=tool.name,
            args=tool.inputSchema if hasattr(tool, "inputSchema") else {},
        )
        dspy_tools.append(sync_tool)

    return dspy_tools


async def call_mcp_tool(server_params, tool_name, tool_args):
    """Create a new session and call the tool"""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Call the tool directly using the session
            result = await session.call_tool(tool_name, arguments=tool_args)
            return result.content[0].text if result.content else None
