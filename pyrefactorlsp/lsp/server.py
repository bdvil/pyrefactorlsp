from pathlib import Path

import click
import libcst
from lsprotocol.types import (
    CODE_ACTION_RESOLVE,
    INITIALIZED,
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_SAVE,
    CodeAction,
    CodeActionDisabledType,
    CodeActionKind,
    CodeActionOptions,
    CodeActionParams,
    Command,
    DidSaveTextDocumentParams,
    InitializedParams,
)
from pygls.server import LanguageServer

from pyrefactorlsp import LOGGER, __version__
from pyrefactorlsp.config import load_config
from pyrefactorlsp.refactor.config import Config
from pyrefactorlsp.refactor.graph import (
    Graph,
    build_project_graph,
    get_module_dependencies,
)
from pyrefactorlsp.refactor.load import get_project_config


class RefactorServer(LanguageServer):
    def __init__(self, version: str):
        super().__init__("pyrefactorlsp", version)
        self.configs: dict[str, Config] = {}
        self.graphs: dict[str, Graph] = {}

    def build_graph(self, workspace_uri: str) -> None:
        if not workspace_uri.startswith("file://"):
            return
        workspace_uri = workspace_uri.removeprefix("file://")
        if workspace_uri not in self.configs:
            config = get_project_config(workspace_uri)
            self.configs[workspace_uri] = config
            self.graphs[workspace_uri] = build_project_graph(config)

    def update_file_deps(self, file_uri: str) -> None:
        if not file_uri.endswith(".py"):
            return
        if not file_uri.startswith("file://"):
            return
        file_uri = file_uri.removeprefix("file://")
        cst: None | libcst.Module = None
        for workspace_url, graph in self.graphs.items():
            if not file_uri.startswith(workspace_url):
                continue
            file_package = (
                file_uri.removeprefix(workspace_url)
                .removeprefix("/")
                .removesuffix(".py")
                .replace("/", ".")
            )
            for mod in graph.nodes:
                if mod.full_mod_name == file_package:
                    if cst is None:
                        cst = libcst.parse_module(
                            self.workspace.get_document(file_uri).source
                        )
                    mod.cst = cst.deep_clone()
                    graph.reset_dependencies(mod)
                    dependencies = get_module_dependencies(graph, mod)
                    for dependency in dependencies:
                        graph.add_edge((mod, dependency))


server = RefactorServer(f"v{__version__}")


@server.feature(INITIALIZED)
def did_initialized(ls: LanguageServer, params: InitializedParams):
    LOGGER.debug("Did initialized: %s", params)
    for folder in ls.workspace.folders:
        server.build_graph(folder)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: DidSaveTextDocumentParams):
    """Text document did save notification."""
    LOGGER.debug("TEXT_DOCUMENT_DID_SAVE: %s", params)
    server.update_file_deps(params.text_document.uri)


@server.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(code_action_kinds=[CodeActionKind.Refactor]),
)
def code_actions(params: CodeActionParams):
    LOGGER.debug("TEXT_DOCUMENT_CODE_ACTION: %s", params)
    action = CodeAction(
        title="Move symbol",
        kind="refactor.move",
        command=Command(
            title="Start moving symbol",
            command="codeAction.moveSymbol",
            arguments=["test"],
        ),
    )
    return [action]


@server.command("codeAction.moveSymbol")
def move_symbol_command(ls: LanguageServer, args):
    LOGGER.debug("codeAction.moveSymbol: %s", args)


@click.command("serve")
def serve():
    config = load_config()

    print(f"Start server at {config.server_url}:{config.server_port}")
    server.start_tcp(config.server_url, config.server_port)
