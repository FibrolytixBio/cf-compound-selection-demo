import fcntl
import json
import time
import asyncio
from pathlib import Path


class FileBasedRateLimiter:
    def __init__(
        self, max_requests: int = 3, time_window: float = 1.0, name: str = "default"
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.state_file = Path(f"/tmp/{name}_rate_limiter.json")

    async def acquire(self):
        """Async version for async use"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._acquire_sync)

    def acquire_sync(self):
        """Synchronous version for non-async use"""
        self._acquire_sync()

    def _acquire_sync(self):
        # Create file if it doesn't exist
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"requests": []}))

        # Acquire exclusive lock
        with open(self.state_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                current_time = time.time()

                # Clean old requests
                data["requests"] = [
                    req
                    for req in data["requests"]
                    if current_time - req < self.time_window
                ]

                # Check if we need to wait
                if len(data["requests"]) >= self.max_requests:
                    oldest = data["requests"][0]
                    wait_time = self.time_window - (current_time - oldest)
                    if wait_time > 0:
                        time.sleep(wait_time)
                        current_time = time.time()
                        data["requests"] = [
                            req
                            for req in data["requests"]
                            if current_time - req < self.time_window
                        ]

                # Add current request
                data["requests"].append(current_time)

                # Write back
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


## OLD CODEEE

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

    # Convert file path to module path
    # Remove .py extension and convert path separators to dots
    module_path = str(path_to_mcp_server).replace(".py", "")

    # Find the project root (where agentic_system package starts)
    parts = module_path.split("/")
    try:
        # Find where 'agentic_system' appears in the path
        agentic_index = parts.index("agentic_system")
        # Take everything from 'agentic_system' onwards
        module_name = ".".join(parts[agentic_index:])
    except ValueError:
        # Fallback: assume the path is relative to current working directory
        module_name = module_path.replace("/", ".")

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "-m", module_name],
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
