# Xpra MCP Server Examples

This directory contains example scripts for testing and using the Xpra MCP server.

## Prerequisites

1. Install the required packages:
   ```bash
   pip install mcp
   ```

2. Make sure the Xpra MCP server is running:
   ```bash
   mcp-xpra --debug
   ```

3. For VNC testing, install a VNC client:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tigervnc-viewer

   # Fedora/RHEL
   sudo dnf install tigervnc
   ```

## Example Scripts

### 1. HTML5 Mode Test (`test_client.py`)

Tests the Xpra MCP server using HTML5 mode, which allows accessing applications through a web browser.

```bash
python test_client.py
```

The script will:
1. Start Firefox in HTML5 mode
2. List active sessions
3. Wait 30 seconds for manual testing
4. Stop the session

During the 30-second wait, you can:
- Open your web browser
- Navigate to the URL shown in the output (usually http://localhost:8080)
- Interact with the Firefox window

### 2. VNC Mode Test (`test_vnc_client.py`)

Tests the Xpra MCP server using VNC mode, which allows accessing applications through a VNC client.

```bash
python test_vnc_client.py
```

The script will:
1. Configure the firewall for VNC access
2. Start Firefox in VNC mode with encryption enabled
3. List active sessions
4. Wait 30 seconds for manual testing
5. Stop the session

During the 30-second wait, you can:
- Open your VNC client
- Connect to the address shown in the output (usually localhost:5900)
- Interact with the Firefox window

## Troubleshooting

1. **Connection Refused**
   - Ensure the Xpra MCP server is running (`mcp-xpra --debug`)
   - Check if the ports are open (5900 for VNC, 8080 for HTML5)
   - Verify your firewall settings

2. **Application Doesn't Start**
   - Check the server logs (`~/.local/share/mcp-xpra-server/logs/xpra-server.log`)
   - Ensure Firefox is installed on the server
   - Verify Xpra is installed correctly

3. **VNC Connection Issues**
   - Make sure a VNC client is installed
   - Check if the port is already in use
   - Try disabling encryption if connection fails

4. **HTML5 Connection Issues**
   - Try a different web browser
   - Clear browser cache
   - Check browser console for errors

## Configuration

The server configuration is located at:
- Default: `~/.config/mcp-xpra-server/xpra.yaml`
- System-wide: `/etc/mcp-xpra-server/xpra.yaml`

You can modify settings like:
- VNC/HTML5 ports
- Bind address
- Logging options 