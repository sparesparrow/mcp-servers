"""JSON schemas for MCP tool definitions."""

START_APPLICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "application": {
            "type": "string",
            "description": "Name of the application to start"
        },
        "mode": {
            "type": "string",
            "enum": ["vnc", "html5"],
            "default": "vnc",
            "description": "Display mode for the session"
        },
        "display": {
            "type": "string",
            "pattern": "^:[0-9]+$",
            "default": ":0",
            "description": "X display number"
        },
        "enable_audio": {
            "type": "boolean",
            "default": False,
            "description": "Enable audio forwarding"
        },
        "enable_encryption": {
            "type": "boolean",
            "default": False,
            "description": "Enable AES encryption (VNC mode only)"
        },
        "password_file": {
            "type": "string",
            "description": "Path to password file for authentication"
        }
    },
    "required": ["application"],
    "additionalProperties": False
}

STOP_SESSION_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]+_:[0-9]+$",
            "description": "ID of the session to stop (format: 'application_display')"
        }
    },
    "required": ["session_id"],
    "additionalProperties": False
}

CONFIGURE_FIREWALL_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["vnc", "html5"],
            "default": "vnc",
            "description": "Display mode to configure"
        }
    },
    "additionalProperties": False
}

LIST_SESSIONS_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
} 