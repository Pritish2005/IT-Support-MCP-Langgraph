import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("document_reader")

@mcp.tool()
def read_document(issue_type: str) -> str:
    """Read issue specific documentation. Issue types can be vpn, wifi, hardware, etc."""
    path = f"./docs/{issue_type}.txt"
    try:
        if not os.path.exists(path):
            return f"Documentation not found for: {issue_type}"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading document: {e}"

@mcp.prompt()
def system_prompt() -> str:
    return (
        "You are a support assistant. "
        "Your job is to answer user issues strictly using documentation provided via tools. "
        "If information is not found in the docs, respond with 'I don't have enough documentation to answer that.'"
    )

if __name__ == "__main__":
    mcp.run()
