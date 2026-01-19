#!/bin/bash
#
# MCP Client Installer for VS Code
# 
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/your-org/your-repo/main/install-mcp.sh | bash
#   
# Or locally:
#   ./install-mcp.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# MCP Configuration
MCP_SERVER_NAME="cicd-mcp"
MCP_SERVER_URL="http://localhost:8080/mcp"
MCP_SERVER_TYPE="sse"
MCP_SERVER_DESCRIPTION="MCP server with RAG search and CI/CD query tools"

# VS Code MCP settings path for macOS
VSCODE_MCP_CONFIG="$HOME/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json"

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Check if running on macOS
check_os() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is designed for macOS only."
        log_info "For other platforms, manually edit your MCP settings file."
        exit 1
    fi
}

# Check if VS Code is installed
check_vscode() {
    if [ ! -d "/Applications/Visual Studio Code.app" ] && [ ! -d "$HOME/Applications/Visual Studio Code.app" ]; then
        log_warn "VS Code not found in /Applications"
        log_info "If VS Code is installed elsewhere, the script will still attempt to configure MCP settings."
    fi
}

# Create backup of existing config
backup_config() {
    local config_file=$1
    
    if [ -f "$config_file" ]; then
        local backup_file="${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$config_file" "$backup_file"
        log_info "Created backup: $backup_file"
    fi
}

# Check if jq is available
has_jq() {
    command -v jq >/dev/null 2>&1
}

# Install MCP config using jq (preferred method)
install_with_jq() {
    local config_file=$1
    
    log_info "Using jq for JSON manipulation..."
    
    # Create config directory if it doesn't exist
    mkdir -p "$(dirname "$config_file")"
    
    # Initialize file if it doesn't exist
    if [ ! -f "$config_file" ]; then
        echo '{"mcpServers":{},"inputs":[]}' > "$config_file"
        log_info "Created new MCP settings file"
    fi
    
    # Backup existing config
    backup_config "$config_file"
    
    # Check if server already exists
    if jq -e ".mcpServers.\"$MCP_SERVER_NAME\"" "$config_file" >/dev/null 2>&1; then
        log_warn "MCP server '$MCP_SERVER_NAME' already exists in configuration"
        read -p "Do you want to overwrite it? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled"
            exit 0
        fi
    fi
    
    # Add or update the MCP server configuration
    jq --arg name "$MCP_SERVER_NAME" \
       --arg url "$MCP_SERVER_URL" \
       --arg type "$MCP_SERVER_TYPE" \
       --arg desc "$MCP_SERVER_DESCRIPTION" \
       '.mcpServers[$name] = {
           "url": $url,
           "type": $type,
           "description": $desc
       }' "$config_file" > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"
    
    log_success "MCP server '$MCP_SERVER_NAME' installed successfully!"
}

# Install MCP config using Python (fallback method)
install_with_python() {
    local config_file=$1
    
    log_info "Using Python for JSON manipulation..."
    
    # Create config directory if it doesn't exist
    mkdir -p "$(dirname "$config_file")"
    
    # Backup existing config
    if [ -f "$config_file" ]; then
        backup_config "$config_file"
    fi
    
    # Use Python to manipulate JSON
    python3 - <<EOF
import json
import os
from pathlib import Path

config_file = "$config_file"
server_name = "$MCP_SERVER_NAME"
server_config = {
    "url": "$MCP_SERVER_URL",
    "type": "$MCP_SERVER_TYPE",
    "description": "$MCP_SERVER_DESCRIPTION"
}

# Read existing config or create new one
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
else:
    config = {"mcpServers": {}, "inputs": []}

# Ensure mcpServers exists
if "mcpServers" not in config:
    config["mcpServers"] = {}

# Check if server already exists
if server_name in config["mcpServers"]:
    print(f"WARNING: MCP server '{server_name}' already exists")
    response = input("Do you want to overwrite it? (y/N) ")
    if response.lower() != 'y':
        print("Installation cancelled")
        exit(0)

# Add or update server
config["mcpServers"][server_name] = server_config

# Ensure inputs exists
if "inputs" not in config:
    config["inputs"] = []

# Write back to file
Path(config_file).parent.mkdir(parents=True, exist_ok=True)
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ MCP server '{server_name}' installed successfully!")
EOF
}

# Install MCP config using sed (last resort - basic append only)
install_with_sed() {
    local config_file=$1
    
    log_warn "Neither jq nor Python available. Using basic sed method..."
    log_warn "This method has limitations and may not work for all configurations."
    
    # Create config directory if it doesn't exist
    mkdir -p "$(dirname "$config_file")"
    
    # Backup existing config
    if [ -f "$config_file" ]; then
        backup_config "$config_file"
        log_error "Manual configuration required for existing config file."
        log_info "Please manually add the following to your MCP settings:"
        cat <<EOF

{
  "mcpServers": {
    "$MCP_SERVER_NAME": {
      "url": "$MCP_SERVER_URL",
      "type": "$MCP_SERVER_TYPE",
      "description": "$MCP_SERVER_DESCRIPTION"
    }
  }
}
EOF
        exit 1
    else
        # Create new config file
        cat > "$config_file" <<EOF
{
  "mcpServers": {
    "$MCP_SERVER_NAME": {
      "url": "$MCP_SERVER_URL",
      "type": "$MCP_SERVER_TYPE",
      "description": "$MCP_SERVER_DESCRIPTION"
    }
  },
  "inputs": []
}
EOF
        log_success "Created new MCP configuration file"
    fi
}

# Main installation function
install_mcp() {
    local config_file=$1
    
    if has_jq; then
        install_with_jq "$config_file"
    elif command -v python3 >/dev/null 2>&1; then
        install_with_python "$config_file"
    else
        install_with_sed "$config_file"
    fi
}

# Display next steps
show_next_steps() {
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "Installation Complete!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Make sure your MCP server is running:"
    echo -e "     ${YELLOW}docker-compose up -d${NC}"
    echo ""
    echo "  2. Verify the server is accessible:"
    echo -e "     ${YELLOW}curl http://localhost:8080/health${NC}"
    echo ""
    echo "  3. Restart VS Code to load the new MCP configuration"
    echo ""
    echo -e "${BLUE}Configuration Location:${NC}"
    echo "  $VSCODE_MCP_CONFIG"
    echo ""
    echo -e "${BLUE}To verify the configuration:${NC}"
    echo -e "  ${YELLOW}cat \"$VSCODE_MCP_CONFIG\" | jq '.mcpServers.\"$MCP_SERVER_NAME\"'${NC}"
    echo ""
    echo -e "${BLUE}To remove this MCP server:${NC}"
    echo -e "  ${YELLOW}./install-mcp.sh --uninstall${NC}"
    echo ""
}

# Uninstall MCP server
uninstall_mcp() {
    local config_file=$1
    
    if [ ! -f "$config_file" ]; then
        log_error "MCP configuration file not found"
        exit 1
    fi
    
    log_info "Removing MCP server '$MCP_SERVER_NAME'..."
    
    # Backup before uninstalling
    backup_config "$config_file"
    
    if has_jq; then
        jq "del(.mcpServers.\"$MCP_SERVER_NAME\")" "$config_file" > "${config_file}.tmp" && \
            mv "${config_file}.tmp" "$config_file"
        log_success "MCP server '$MCP_SERVER_NAME' removed successfully!"
    elif command -v python3 >/dev/null 2>&1; then
        python3 - <<EOF
import json
config_file = "$config_file"
with open(config_file, 'r') as f:
    config = json.load(f)
if "mcpServers" in config and "$MCP_SERVER_NAME" in config["mcpServers"]:
    del config["mcpServers"]["$MCP_SERVER_NAME"]
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print("✓ MCP server '$MCP_SERVER_NAME' removed successfully!")
else:
    print("MCP server '$MCP_SERVER_NAME' not found in configuration")
EOF
    else
        log_error "Cannot uninstall: jq or Python required"
        exit 1
    fi
}

# Parse command line arguments
parse_args() {
    case "${1:-}" in
        --uninstall|-u)
            check_os
            uninstall_mcp "$VSCODE_MCP_CONFIG"
            exit 0
            ;;
        --help|-h)
            cat <<EOF
MCP Client Installer for VS Code

Usage:
  $0                 Install MCP server configuration
  $0 --uninstall     Remove MCP server configuration
  $0 --help          Show this help message

Configuration:
  Server Name: $MCP_SERVER_NAME
  Server URL:  $MCP_SERVER_URL
  Server Type: $MCP_SERVER_TYPE

For more information, visit: https://github.com/your-org/your-repo
EOF
            exit 0
            ;;
        "")
            # Default action: install
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

# Main script execution
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  MCP Client Installer for VS Code"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    parse_args "$@"
    
    check_os
    check_vscode
    
    log_info "Installing MCP server: $MCP_SERVER_NAME"
    log_info "Server URL: $MCP_SERVER_URL"
    echo ""
    
    install_mcp "$VSCODE_MCP_CONFIG"
    
    show_next_steps
}

# Run main function
main "$@"
