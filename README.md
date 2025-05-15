# SSB MCP

[Model context protocol (MCP)](https://modelcontextprotocol.io/) for communicating with [Statistics Norway / Statistisk sentralbyrå (SSB)](https://www.ssb.no/).

This MCP server supports the following operations:

1. Use the Search API to find statistics based on keywords.
2. Fetch statistics table metadata.
3. Read the statistics table data.
4. List the latest publications for a given date.

## Getting Started

### Prerequisites

Make sure you have [`uv`](https://docs.astral.sh/uv/) installed on your machine. You can install it with:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

1. Clone the repository with:

    ```shell
    git clone https://github.com/FredrikBakken/ssb_mcp
    ```
   
2. Install the project dependencies:

    ```shell
    cd ssb_mcp/
    uv sync
    ```

3. Configure [Claude Desktop](https://claude.ai/download) by adding the following settings to `~/.config/Claude/claude_desktop_config.json`:

    ```shell
    {
      "mcpServers": {
        "ssb": {
          "command": "uv",
          "args": [
            "--directory",
            "/<path>/ssb_mcp",
            "run",
            "ssb_mcp/main.py"
          ]
        }
      }
    }
    ```
   
    PS: Make sure to change the `<path>` value first.

Now you're all set - next step is to open the Claude Desktop application on your machine.
