"""`crayonlark` command line. Used by compose commands, make targets and by me."""

from __future__ import annotations

import getpass

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("garage-init")
def garage_init(capacity_gb: int = 150) -> None:
    """Create Garage layout, key and buckets (idempotent)."""
    from crayonlark.core import garage_init as gi

    buckets = gi.run(capacity_gb)
    typer.echo(f"garage ready: {', '.join(buckets)}")


@app.command()
def migrate() -> None:
    """Apply database migrations (alembic upgrade head) and seed default settings."""
    from crayonlark.core.migrate import upgrade_and_seed

    upgrade_and_seed()
    typer.echo("database migrated")


@app.command("create-admin")
def create_admin(email: str = typer.Option(..., prompt=True)) -> None:
    """Create or reset the single admin user."""
    from crayonlark.core.auth import upsert_admin

    password = getpass.getpass("Password (min 12 chars): ")
    if len(password) < 12:
        raise typer.BadParameter("password must be at least 12 characters")
    upsert_admin(email, password)
    typer.echo(f"admin {email} saved")


@app.command()
def demo(out: str = "/demo-output") -> None:
    """Run the full pipeline on the 5 bundled sample images (no paid API calls)."""
    from pathlib import Path

    from crayonlark.demo import run

    typer.echo("Crayonlark demo (manual mode, zero paid calls)")
    res = run(Path(out))
    typer.echo("\nOutput files:")
    for f in res["files"]:
        typer.echo(f"  {f}")


if __name__ == "__main__":
    app()
