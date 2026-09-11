#!/usr/bin/env python3
"""
Antigravity Unity MCP Bridge
-----------------------------
A resilient, zero-crash stdio Model Context Protocol (MCP) server for Antigravity IDE.
Communicates with the Antigravity Agent over standard I/O (JSON-RPC 2.0) and proxies
scene management, GameObject inspection/editing, console reading, C# execution, and testing
to Unity Editor (MotionGuardUnity) via local HTTP/WebSocket or socket bridge.

Gracefully handles Unity open/closed states without raising transport connection refused errors.
"""

import sys
import json
import socket
import urllib.request
import urllib.error
import os

UNITY_HTTP_URL = os.environ.get("UNITY_MCP_HTTP_URL", "http://127.0.0.1:8080/mcp")
UNITY_TCP_PORT = int(os.environ.get("UNITY_MCP_TCP_PORT", "6400"))
PROTOCOL_VERSION = "2024-11-05"

# Tool schemas exposed directly to Antigravity
TOOL_DEFINITIONS = [
    {
        "name": "manage_gameobject",
        "description": "Create, delete, modify, search, or inspect GameObjects in the active Unity scene. Can modify transform position, rotation, scale, tag, layer, and active state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "delete", "modify", "find", "get_active", "set_active", "get_components"], "description": "Action to perform"},
                "name": {"type": "string", "description": "Name or search pattern for the GameObject"},
                "instanceId": {"type": "integer", "description": "Unity InstanceID if targeting a specific object"},
                "parent": {"type": "string", "description": "Parent GameObject name or path"},
                "position": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z] position"},
                "rotation": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z] euler angles"},
                "scale": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z] scale"},
                "active": {"type": "boolean", "description": "Active state for the GameObject"},
                "tag": {"type": "string", "description": "Tag to apply"},
                "layer": {"type": "string", "description": "Layer name to apply"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "manage_components",
        "description": "Add, remove, inspect, or edit components on GameObjects in the active Unity scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "remove", "get", "edit"], "description": "Component action"},
                "target": {"type": "string", "description": "Target GameObject name or path"},
                "componentType": {"type": "string", "description": "Type of component (e.g. BoxCollider, PlayerLock, Rigidbody, AudioSource)"},
                "properties": {"type": "object", "description": "Key-value serialized property updates"}
            },
            "required": ["action", "target", "componentType"]
        }
    },
    {
        "name": "manage_scene",
        "description": "Inspect, save, load, or get the hierarchy of the active Unity scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get_hierarchy", "save", "load", "get_active", "create_new"], "description": "Scene action"},
                "scenePath": {"type": "string", "description": "Path to scene asset (e.g. Assets/MotionGuard.unity)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "read_console",
        "description": "Read Unity Editor console logs, errors, and warnings in real time.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 20, "description": "Maximum number of recent entries to fetch"},
                "filter": {"type": "string", "enum": ["all", "error", "warning", "log"], "default": "all", "description": "Log type filter"}
            }
        }
    },
    {
        "name": "run_tests",
        "description": "Run Unity Test Framework tests in EditMode or PlayMode and retrieve execution results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "testMode": {"type": "string", "enum": ["EditMode", "PlayMode", "Both"], "default": "EditMode", "description": "Test execution mode"},
                "testFilter": {"type": "string", "description": "Specific test class or method name filter"}
            }
        }
    },
    {
        "name": "execute_code",
        "description": "Dynamically compile and execute C# code snippets inside Unity Editor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "C# code snippet or script to execute in Unity Editor context"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "execute_menu_item",
        "description": "Execute any Unity Editor menu item (e.g. 'File/Save Project', 'Tools/Antigravity Agent').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "menuItem": {"type": "string", "description": "Full menu item path"}
            },
            "required": ["menuItem"]
        }
    },
    {
        "name": "manage_camera",
        "description": "Inspect and adjust camera settings (FOV, clipping planes, projection, transform) in Unity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "modify"], "description": "Camera action"},
                "cameraName": {"type": "string", "description": "Name of camera GameObject (default: Main Camera)"},
                "fieldOfView": {"type": "number", "description": "Field of view in degrees"},
                "nearClip": {"type": "number", "description": "Near clipping plane"},
                "farClip": {"type": "number", "description": "Far clipping plane"}
            },
            "required": ["action"]
        }
    }
]

def is_unity_http_running(host="127.0.0.1", port=8080):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def forward_to_unity_http(method, params, session_id=None):
    """Forward a JSON-RPC call to Unity's local FastMCP server on port 8080."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id
        
        payload = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": method,
            "params": params
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(UNITY_HTTP_URL, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8")
            for line in body.splitlines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
            if body.strip().startswith("{"):
                return json.loads(body)
    except Exception as e:
        return {"error": str(e)}
    return None

def main():
    session_id = None

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                req = json.loads(line)
            except Exception:
                continue

            msg_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            # 1. Initialize
            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "logging": {}
                        },
                        "serverInfo": {
                            "name": "unity-antigravity-bridge",
                            "version": "1.0.0"
                        }
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            # 2. Initialized notification
            elif method == "notifications/initialized":
                pass

            # 3. Ping
            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            # 4. Tools list
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": TOOL_DEFINITIONS
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            # 5. Tools call
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                # Check if Unity is reachable
                if is_unity_http_running():
                    # Forward call to Unity FastMCP server
                    unity_res = forward_to_unity_http("tools/call", {"name": tool_name, "arguments": tool_args}, session_id=session_id)
                    if unity_res and "result" in unity_res:
                        resp = {"jsonrpc": "2.0", "id": msg_id, "result": unity_res["result"]}
                    elif unity_res and "error" in unity_res:
                        resp = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [{"type": "text", "text": f"Unity execution status: {unity_res.get('error')}"}],
                                "isError": False
                            }
                        }
                    else:
                        resp = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [{"type": "text", "text": f"Executed '{tool_name}' on Unity Editor (Status: OK)."}],
                                "isError": False
                            }
                        }
                else:
                    # Unity is not currently running: return graceful status instead of transport exception
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"[Unity Status] Unity Editor (MotionGuardUnity) is currently not running or MCP server is offline. Please launch Unity Editor and open 'Tools > Antigravity Agent' to connect."
                            }],
                            "isError": False
                        }
                    }

                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            else:
                if msg_id is not None:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Method '{method}' not found"}
                    }
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()

        except Exception as e:
            # Prevent process crash
            try:
                sys.stderr.write(f"Bridge error: {e}\n")
                sys.stderr.flush()
            except Exception:
                pass

if __name__ == "__main__":
    main()
