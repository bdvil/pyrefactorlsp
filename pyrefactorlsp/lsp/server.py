import click
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
)
from pygls.server import LanguageServer

from pyrefactorlsp import LOGGER, __version__
from pyrefactorlsp.config import load_config

server = LanguageServer("pyrefactorlsp", f"v{__version__}")


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    LOGGER.debug("TEXT_DOCUMENT_DID_CHANGE: %s", params)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: LanguageServer, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    ls.show_message("Text Document Did Close")
    LOGGER.debug("TEXT_DOCUMENT_DID_CLOSE: %s", params)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.show_message("Text Document Did Open")
    LOGGER.debug("TEXT_DOCUMENT_DID_OPEN: %s", params)
    print(ls.workspace.folders)


@click.command("serve")
def serve():
    config = load_config()

    print(f"Start server at {config.server_url}:{config.server_port}")
    server.start_tcp(config.server_url, config.server_port)
