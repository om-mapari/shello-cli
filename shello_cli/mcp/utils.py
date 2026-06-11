from fastmcp.mcp_config import MCPConfig
from shello_cli.mcp.client import MCPClient


async def _connect_and_list_tools(client: MCPClient) -> None:
    """Connect to MCP servers and retrieve available tools."""
    await client.connect_async()
    tools = await client.list_tools()
    client._tools = tools


def create_mcp_client(config: dict, timeout: float = 30.0) -> MCPClient:
    """Initialize an MCPClient with the given servers configuration.

    Connects to the servers, queries their tools, and returns the client.
    """
    # Normalize configuration format to match fastmcp.mcp_config.MCPConfig
    if "mcpServers" not in config and "mcp_servers" not in config:
        normalized_config = {"mcpServers": config}
    elif "mcp_servers" in config and "mcpServers" not in config:
        normalized_config = {"mcpServers": config["mcp_servers"]}
    else:
        normalized_config = config

    mcp_config = MCPConfig.model_validate(normalized_config)
    client = MCPClient(mcp_config)

    try:
        client.call_async_from_sync(
            _connect_and_list_tools, timeout=timeout, client=client
        )
    except Exception as e:
        client.sync_close()
        raise e

    return client
