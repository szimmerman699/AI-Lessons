#!/usr/bin/env python3
"""
Hook to block dangerous git operations that could commit .env files or secrets.
Reads JSON from stdin and outputs JSON to block the action.
"""
import sys
import json

# Read hook input from stdin
try:
    hook_input = json.load(sys.stdin)
except (json.JSONDecodeError, EOFError):
    # If input parsing fails, allow the command
    print(json.dumps({"continue": True}))
    sys.exit(0)

command = hook_input.get("tool_input", {}).get("command", "")

# Dangerous patterns that should be blocked
dangerous_patterns = [
    ".env",  # Any .env file
    "push --force",  # Force push
    "push -f",  # Force push short form
    "reset --hard",  # Hard reset
]

# Check if command matches dangerous patterns
for pattern in dangerous_patterns:
    if pattern in command:
        response = {
            "continue": False,
            "stopReason": f"❌ BLOCKED: Command contains '{pattern}'. Reason: Prevents accidental commit of .env files or destructive operations"
        }
        print(json.dumps(response))
        sys.exit(0)  # Exit 0, let the response block it

# Allow safe commands
print(json.dumps({"continue": True}))
sys.exit(0)
