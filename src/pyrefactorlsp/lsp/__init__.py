import click

from .server import serve


@click.group()
def root():
    pass


root.add_command(serve)
