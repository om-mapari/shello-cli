from shello_cli.tools.base import ShelloToolBase
from shello_cli.types import ToolResult, ShelloTool
from shello_cli.mcp.client import MCPClient


class MCPToolWrapper(ShelloToolBase):
    """Wrapper that exposes an MCP tool as a standard Shello CLI tool."""

    def __init__(self, mcp_client: MCPClient, mcp_tool):
        self._client = mcp_client
        self._tool_def = mcp_tool
        self.tool_name = mcp_tool.name

    @property
    def schema(self) -> ShelloTool:
        """Return the OpenAI function-calling schema for this MCP tool."""
        parameters = self._tool_def.inputSchema
        if not parameters:
            parameters = {"type": "object", "properties": {}}
        elif isinstance(parameters, dict):
            # Create a copy to avoid mutating the original tool definition schema
            parameters = dict(parameters)
            if "properties" not in parameters:
                parameters["properties"] = {}

        return ShelloTool(
            type="function",
            function={
                "name": self.tool_name,
                "description": self._tool_def.description or "No description provided",
                "parameters": parameters,
            },
        )

    def execute(self, **kwargs) -> ToolResult:
        """Synchronously execute the MCP tool with the given arguments."""
        try:
            # call_tool_mcp is an async method on fastmcp.Client
            result = self._client.call_async_from_sync(
                self._client.call_tool_mcp,
                name=self.tool_name,
                arguments=kwargs,
                timeout=300.0,  # 5-minute timeout for execution
            )

            # Build standard string output from content blocks
            output_parts = []
            for block in result.content:
                if hasattr(block, "text") and block.text:
                    output_parts.append(block.text)
                elif hasattr(block, "data"):
                    mime = getattr(block, "mimeType", "image/*")
                    output_parts.append(f"[Image content: {mime}]")
                else:
                    output_parts.append(str(block))

            text = "\n".join(output_parts)

            if getattr(result, "isError", False):
                return ToolResult(success=False, error=text)
            else:
                return ToolResult(success=True, output=text)

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error executing MCP tool '{self.tool_name}': {e}",
            )
