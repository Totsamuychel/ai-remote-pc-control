#!/usr/bin/env python3
"""Entry point for AI Remote PC Control MCP Agent.

Supports standard input/output (stdio) for local and SSH-tunneled agent sessions,
as well as Server-Sent Events (SSE) for private network setups (Tailscale/WireGuard).
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure agent directory is in Python path
AGENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = AGENT_DIR.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.mcp_server import create_mcp_server
from agent.safety.audit import AuditLogger
from agent.safety.policy import SecurityPolicy


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Remote PC Control - Model Context Protocol (MCP) Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Communication transport protocol",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="Host address to bind for SSE transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to bind for SSE transport",
    )
    parser.add_argument(
        "--config",
        default=str(AGENT_DIR / "config.yaml"),
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--mode",
        choices=["read-only", "safe-execute", "full-control"],
        default=None,
        help="Override security policy mode",
    )
    return parser.parse_args()


def print_banner(mode: str, transport: str, allowed_dirs: list):
    banner = f"""
===================================================================
           AI Remote PC Control - MCP Server v0.1.0
===================================================================
[*] Transport   : {transport.upper()}
[*] Security Mode: {mode.upper()}
[*] Allowed Dirs: {', '.join(allowed_dirs)}
[*] Audit Log   : Active (logs/audit.jsonl)
===================================================================
"""
    # Write banner to stderr so stdio JSON-RPC on stdout is not corrupted
    sys.stderr.write(banner + "\n")
    sys.stderr.flush()


def main():
    args = parse_args()

    # Apply mode override if specified via CLI
    if args.mode:
        os.environ["SECURITY_MODE"] = args.mode

    # Initialize security policy and audit logger
    policy = SecurityPolicy.get_instance(config_path=args.config)
    if args.mode:
        policy.mode = args.mode

    audit_path = policy.config.get("audit", {}).get("log_file", "logs/audit.jsonl")
    if not Path(audit_path).is_absolute():
        audit_path = str(AGENT_DIR / audit_path)
    logger = AuditLogger.get_instance(log_path=audit_path)

    print_banner(
        mode=policy.mode,
        transport=args.transport,
        allowed_dirs=[str(d) for d in policy.allowed_directories],
    )

    # Initialize FastMCP Server
    server_name = policy.config.get("server", {}).get("name", "RemotePCControl")
    mcp = create_mcp_server(name=server_name, config_path=args.config)

    # Launch server
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        # Configure FastMCP settings for SSE if applicable
        if hasattr(mcp, "settings"):
            mcp.settings.host = args.host
            mcp.settings.port = args.port
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
