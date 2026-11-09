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


@app.command("etsy-taxonomy")
def etsy_taxonomy(search: str = "coloring") -> None:
    """Find the Etsy seller taxonomy id for ETSY_TAXONOMY_ID (needs Etsy connected)."""
    from crayonlark.core.db import session_scope
    from crayonlark.integrations.etsy import Etsy

    def walk(nodes: list[dict], path: str = "") -> None:
        for n in nodes:
            full = f"{path} > {n['name']}" if path else n["name"]
            if search.lower() in full.lower():
                typer.echo(f"{n['id']:>6}  {full}")
            walk(n.get("children") or [], full)

    with session_scope() as s:
        walk(Etsy(s).taxonomy())


@app.command()
def backup() -> None:
    """Run the backup now (database dump + file mirror, 14-day retention)."""
    import json

    from crayonlark.core import backup as bk

    typer.echo(json.dumps(bk.run(), indent=2, default=str))


@app.command("backup-list")
def backup_list() -> None:
    """List the database dumps you can restore."""
    from crayonlark.core import backup as bk

    st = bk.status()
    for name in st["dumps"]:
        typer.echo(name.removeprefix("crayonlark-").removesuffix(".dump"))
    if not st["dumps"]:
        typer.echo("no backups yet")


@app.command()
def restore(
    day: str = typer.Option(..., help="YYYY-MM-DD, see `crayonlark backup-list`"),
    yes: bool = typer.Option(False, "--yes", help="really replace the database"),
) -> None:
    """Restore the database from that night's dump and put mirrored files back in Garage."""
    from crayonlark.core import backup as bk

    if not yes:
        typer.confirm(
            f"This REPLACES the whole database with the backup from {day}. Continue?", abort=True
        )
    typer.echo(bk.restore(day))


@app.command("weekly-report")
def weekly_report(send: bool = False) -> None:
    """Print the weekly report (add --send to also send it by Telegram and email)."""
    from crayonlark.core.db import session_scope
    from crayonlark.reports import weekly

    with session_scope() as s:
        if send:
            typer.echo(weekly.send(s)["text"])
        else:
            typer.echo(weekly.render(weekly.collect(s)))


@app.command("kdp-import")
def kdp_import(path: str) -> None:
    """Import a KDP royalty report CSV (same as admin → Sales → Import)."""
    from pathlib import Path

    from crayonlark.core import sales
    from crayonlark.core.db import session_scope

    with session_scope() as s:
        typer.echo(sales.import_kdp(s, Path(path).read_bytes()))


if __name__ == "__main__":
    app()
