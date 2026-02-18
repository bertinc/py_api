"""Command-line wrapper to run the timesheet Flask app with configurable host/port.

Usage examples:
  python cli.py --host 127.0.0.1 --port 5000
  python cli.py --port 8001 --debug --reload
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from timesheet import app


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments for running the timesheet server.

    Args:
        argv (list[str] | None): Optional list of arguments (for testing).

    Returns:
        argparse.Namespace: Parsed arguments with attributes `host`, `port`,
            `debug`, `reload`, and `quiet`.
    """
    parser = argparse.ArgumentParser(description="Run timesheet API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on (default: 8001)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument("--reload", action="store_true", help="Enable the Werkzeug reloader")
    parser.add_argument("--quiet", action="store_true", help="Suppress startup logging message")
    return parser.parse_args(argv)


def validate_port(port: int) -> None:
    """
    Validate that `port` is within the allowed TCP/UDP port range.

    Args:
        port (int): Port number to validate.

    Raises:
        ValueError: If `port` is not between 1 and 65535 inclusive.
    """
    if not (1 <= port <= 65535):
        raise ValueError("port must be between 1 and 65535")


def main(argv: Optional[list[str]] = None) -> int:
    """
    Entry point to run the Flask `app` with CLI-provided settings.

    Args:
        argv (list[str] | None): Optional argument list (used for tests).

    Returns:
        int: Exit code (0 on success, non-zero on error).
    """
    args = parse_args(argv)

    try:
        validate_port(args.port)
    except Exception as exc:
        print(f"Invalid port: {exc}")
        return 2

    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        logging.info("Starting timesheet server on %s:%d (debug=%s, reload=%s)", args.host, args.port, args.debug, args.reload)

    # Flask's run() accepts `use_reloader`; debug=True also implies the reloader.
    try:
        app.run(debug=args.debug, host=args.host, port=args.port, use_reloader=args.reload)
        return 0
    except Exception as exc:
        print(f"Failed to start server: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
