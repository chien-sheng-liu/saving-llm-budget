"""Entry point for executing the Typer application."""

import sys

from .cli import app


def main() -> None:
    """Invoke the CLI application."""
    try:
        app(standalone_mode=False)
    except SystemExit as exc:
        sys.exit(exc.code)


if __name__ == "__main__":
    main()
