"""Entry point for executing the Typer application."""

from .cli import app


def main() -> None:
    """Invoke the CLI application."""
    app()


if __name__ == "__main__":
    main()
