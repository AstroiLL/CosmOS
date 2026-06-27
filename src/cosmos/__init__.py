"""CosmOS CLI entry point."""

import typer

app = typer.Typer(
    name="cosmos",
    help="CosmOS — настраиваемая агентная ОС",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def callback():
    pass


def main():
    app()
