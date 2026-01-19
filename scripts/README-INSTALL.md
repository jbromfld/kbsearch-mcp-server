# MCP Client Installation

Quick setup for adding the CI/CD MCP server to VS Code.

## One-Line Install (macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/jbromfld/kbsearch-mcp-server/develop/scripts/mcp_installer.sh | bash
```
## Alternative: Download and Run

```bash
# Download the script
curl -fsSL https://raw.githubusercontent.com/jbromfld/kbsearch-mcp-server/develop/scripts/mcp_installer.sh -o install-mcp.sh

# Make it executable
chmod +x install-mcp.sh

# Run it
./install-mcp.sh
```

## What It Does

The installer will:

1. ✅ Detect your VS Code MCP settings location
2. ✅ Create a backup of your existing configuration
3. ✅ Add the CI/CD MCP server configuration
4. ✅ Preserve any existing MCP servers you have configured

## Configuration Added

```json
{
  "servers": {
    "cicd-mcp": {
      "url": "http://localhost:8080/mcp",
      "type": "sse",
      "description": "MCP server with RAG search and CI/CD query tools"
    }
  }
}
```

## Requirements

- **macOS** (for this automated installer)
- **VS Code** with MCP support
- One of the following (installer will auto-detect):
  - `jq` (recommended) - Install: `brew install jq`
  - `python3` (fallback)
  - `sed` (basic support)

## Before Installing

Make sure your MCP server is running:

```bash
# Start the server
docker-compose up -d

# Verify it's running
curl http://localhost:8080/health
```

## After Installing

1. **Restart VS Code** to load the new configuration
2. **Test the connection** in your MCP-enabled tool

## Verify Installation

```bash
# View your MCP configuration
cat "$HOME/Library/Application Support/Code/User/mcp.json" | jq .
```

## Uninstall

To remove the MCP server configuration:

```bash
./install-mcp.sh --uninstall
```

Or manually edit:
```
~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json
```

## Troubleshooting

### Script fails to find VS Code

The installer assumes VS Code is in `/Applications`. If you see warnings but the script completes, check the settings file manually.

### Permission denied

```bash
chmod +x install-mcp.sh
```

### MCP server not responding

Check if the server is running:

```bash
docker ps | grep cicd-mcp
curl http://localhost:8080/health
```

### Want to change the configuration?

Edit the script variables at the top:

```bash
MCP_SERVER_NAME="cicd-mcp"
MCP_SERVER_URL="http://localhost:8080/mcp"
MCP_SERVER_TYPE="sse"
```

## Manual Installation (Any Platform)

If the script doesn't work for your platform, manually edit your MCP settings file:

**VS Code (macOS):**
```
~/Library/Application Support/Code/User/mcp.json
```

**VS Code (Linux):**
```
~/.config/Code/User/mcp.json
```

**VS Code (Windows):**
```
%APPDATA%\Code\User\mcp.json
```

Add this configuration:

```json
{
  "servers": {
    "cicd-mcp": {
      "url": "http://localhost:8080/mcp",
      "type": "sse",
      "description": "MCP server with RAG search and CI/CD query tools"
    }
  },
  "inputs": []
}
```
