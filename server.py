import sys
import json
import os
from pathlib import Path

# Locate the shared ledger file in the workspace
WORKSPACE_DIR = Path(__file__).resolve().parents[1]
LEDGER_PATH = WORKSPACE_DIR / "iwrite" / "credits_ledger.json"

def read_ledger():
    if not LEDGER_PATH.exists():
        # Create a default ledger if it does not exist
        default_data = {
            "credits": 1250,
            "last_updated": "2026-06-30T17:37:13Z",
            "transactions": []
        }
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER_PATH, "w") as f:
            json.dump(default_data, f, indent=2)
        return default_data

    try:
        with open(LEDGER_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"credits": 1250, "transactions": []}

def write_ledger(data):
    try:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Error writing ledger: {e}\n")

def handle_request(req):
    try:
        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "antigravity-credit-tracker",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "get_balance",
                            "description": "Retrieve the current remaining Antigravity credit balance.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "record_transaction",
                            "description": "Log credit usage and update the remaining balance.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "delta": {
                                        "type": "integer",
                                        "description": "Amount of credits to subtract (e.g. 5)"
                                    },
                                    "action": {
                                        "type": "string",
                                        "description": "Description of the credit usage (e.g., 'Code Generation')"
                                    }
                                },
                                "required": ["delta", "action"]
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "get_balance":
                ledger = read_ledger()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Current balance: {ledger.get('credits', 1250)} credits remaining."
                            }
                        ]
                    }
                }

            elif tool_name == "record_transaction":
                delta = int(arguments.get("delta", 0))
                action = arguments.get("action", "Unknown Action")
                
                ledger = read_ledger()
                current_bal = ledger.get("credits", 1250)
                new_bal = max(0, current_bal - delta)
                
                ledger["credits"] = new_bal
                ledger["transactions"].append({
                    "id": f"tx_{int(os.getpid())}_{len(ledger['transactions']) + 1}",
                    "action": action,
                    "delta": -delta,
                    "balance": new_bal
                })
                write_ledger(ledger)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Transaction recorded successfully. {delta} credits deducted. New balance: {new_bal}."
                            }
                        ]
                    }
                }

        # Fallback response for unhandled JSON-RPC methods
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method {method} not found"
            }
        }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req.get("id"),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

def main():
    sys.stderr.write("Antigravity Credit Tracker MCP Server started\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Parse error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
