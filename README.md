# kbsearch-mcp

Minimal MCP (Model Context Protocol) server for local editor integrations.

Quick start
- Create a Python venv and install deps:

	python -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt

- Start the server:

	export MCP_SERVER_NAME=ci-knowledge-mcp
	python server.py

	The server will print its listening URL/port to the console — note the base URL (for example `http://localhost:PORT`).

Editor integrations
If your editor supports connecting to an external MCP-compatible model server, point the editor's MCP/Model-Provider URL to the server base URL printed above (for example `http://localhost:PORT`). Example settings and guidance for common editors:

- VS Code
	- Install your preferred model-provider extension (one that supports MCP/Model Provider Protocol).
	- Example workspace settings (replace PORT):

		{
			"mcp.serverUrl": "http://localhost:PORT",
			"mcp.serverName": "ci-knowledge-mcp"
		}

	- After adding the URL, reload the window and select the provider in the extension's UI.

	- Add to `settings.json` (registry) or `mcp.json`
	  - Some VS Code extensions accept a registry-style setting so multiple providers can be listed. Example `settings.json` entries you can add to either your User or Workspace settings (replace PORT):

		// single-provider form
		{
		  "mcp.serverUrl": "http://localhost:PORT",
		  "mcp.serverName": "ci-knowledge-mcp"
		}

		// registry form (for extensions that support a provider registry)
		{
		  "mcp.registry": [
		    {
		      "name": "ci-knowledge-mcp",
		      "url": "http://localhost:PORT"
		    }
		  ]
		}

	  - Save and reload VS Code; the extension should show the new provider in its configuration UI.

- Cursor
	- Open Cursor settings -> Model Providers (or the equivalent provider configuration UI).
	- Add a custom provider and use the server base URL (for example `http://localhost:PORT`).
	- Mark it enabled for workspace use.

- IntelliJ Community Edition
	- Install a plugin that supports external LLM/MCP providers (if available).
	- In the plugin's provider configuration, add a new provider with the server base URL (for example `http://localhost:PORT`) and optional name `ci-knowledge-mcp`.

Notes
- If your editor/plugin requires an API key or other auth, check `server.py` and the server logs for supported auth options and configure accordingly.
- If you want to bind to a fixed port or host, modify `server.py` to call `mcp.run(host=..., port=...)` or consult the `fastmcp` docs for runtime options.

Contributions and issues
- See `registry.py` to add or remove registered tools.

