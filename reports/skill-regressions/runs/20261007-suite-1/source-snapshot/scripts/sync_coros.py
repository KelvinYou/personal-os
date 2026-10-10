#!/usr/bin/env python3
"""Retired password-based integration; no network calls or file writes."""
from __future__ import annotations

import sys


def main() -> None:
    sys.exit(
        "[Status: Warning] COROS password sync is retired. Connect the official "
        "COROS MCP at https://mcp.coros.com/mcp through your AI client and OAuth. "
        "See docs/design/coros-official-mcp.md. No data was fetched or written."
    )


if __name__ == "__main__":
    main()
