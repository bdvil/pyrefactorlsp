from collections.abc import Generator, Sequence
from dataclasses import dataclass
from subprocess import PIPE, Popen, run
from typing import Literal, cast

import click
import libcst
from lsprotocol.types import (
    INITIALIZED,
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_SAVE,
    CodeAction,
    CodeActionKind,
    CodeActionOptions,
    CodeActionParams,
    Command,
    DidSaveTextDocumentParams,
    InitializedParams,
    OptionalVersionedTextDocumentIdentifier,
    Position,
    Range,
    TextDocumentEdit,
    TextEdit,
    WorkspaceEdit,
)
from pygls.server import LanguageServer

from pyrefactorlsp import LOGGER, __version__
from pyrefactorlsp.config import load_config
from pyrefactorlsp.refactor.actions.move_symbol_source import (
    MoveSymbolSource,
    move_symbol_source,
)
from pyrefactorlsp.refactor.actions.move_symbol_target import move_symbol_target
from pyrefactorlsp.refactor.config import Config
from pyrefactorlsp.refactor.diffs import get_text_edits
from pyrefactorlsp.refactor.graph import (
    Graph,
    build_project_graph,
    get_module_dependencies,
)
from pyrefactorlsp.refactor.load import get_project_config
from pyrefactorlsp.refactor.module import Module


class RefactorServer(LanguageServer):
    def __init__(self, version: str):
        super().__init__("pyrefactorlsp", version)
        self.configs: dict[str, Config] = {}
        self.graphs: dict[str, Graph] = {}
        self.current_moves: dict[str, MoveSymbolSource] = {}

    def get_moves(self, file_uri: str) -> Generator[MoveSymbolSource, None, None]:
        file_uri = file_uri.removeprefix("file://")
        for workspace, move in self.current_moves.items():
            if file_uri.startswith(workspace):
                yield move

    def get_workspace_moves(
        self, file_uri: str
    ) -> Generator[tuple[str, MoveSymbolSource], None, None]:
        file_uri = file_uri.removeprefix("file://")
        for workspace, move in self.current_moves.items():
            if file_uri.startswith(workspace):
                yield workspace, move

    def add_move(self, file_uri: str, move: MoveSymbolSource):
        file_uri = file_uri.removeprefix("file://")
        for workspace in self.configs:
            if file_uri.startswith(workspace):
                self.current_moves[workspace] = move

    def del_move(self, file_uri: str) -> None:
        file_uri = file_uri.removeprefix("file://")
        for workspace in self.configs:
            if file_uri.startswith(workspace) and workspace in self.current_moves:
                del self.current_moves[workspace]

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
        for workspace_uri, graph in self.graphs.items():
            if not file_uri.startswith(workspace_uri):
                continue
            file_package = (
                file_uri.removeprefix(workspace_uri)
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

    def get_mods(
        self, file_uri: str
    ) -> Generator[tuple[str, Graph, Module], None, None]:
        if not file_uri.endswith(".py"):
            return None
        if not file_uri.startswith("file://"):
            return None
        file_uri = file_uri.removeprefix("file://")
        for workspace_uri, graph in self.graphs.items():
            if not file_uri.startswith(workspace_uri):
                continue
            file_package = (
                file_uri.removeprefix(workspace_uri)
                .removeprefix("/")
                .removesuffix(".py")
                .replace("/", ".")
            )
            for mod in graph.nodes:
                if mod.full_mod_name == file_package:
                    yield (workspace_uri, graph, mod)
                    break


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
def code_actions(params: CodeActionParams) -> list[CodeAction]:
    LOGGER.debug("TEXT_DOCUMENT_CODE_ACTION: %s", params)
    for _ in server.get_mods(params.text_document.uri):
        actions = [
            CodeAction(
                title="Move symbol",
                kind="refactor.move",
                command=Command(
                    title="Start moving symbol",
                    command="codeAction.moveSymbol",
                    arguments=[params.text_document.uri, params.range],
                ),
            ),
        ]
        for move in server.get_moves(params.text_document.uri):
            actions.append(
                CodeAction(
                    title=f"Finish moving {move.symbol_name} here",
                    kind="refactor.move",
                    command=Command(
                        title="Finish moving symbol",
                        command="codeAction.finishMoveSymbol",
                        arguments=[params.text_document.uri, params.range],
                    ),
                )
            )
            break
        return actions
    return []


@server.command("codeAction.test")
def test_edits(ls: LanguageServer, arguments):
    document = ls.workspace.get_text_document(arguments[0])
    edit = TextDocumentEdit(
        text_document=OptionalVersionedTextDocumentIdentifier(
            uri=arguments[0], version=document.version
        ),
        edits=[
            TextEdit(
                new_text="This is a test\nThat adds two lines\n",
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=1, character=0),
                ),
            ),
            TextEdit(
                new_text="This is a test\n",
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=2, character=0),
                ),
            ),
        ],
    )
    ls.apply_edit(WorkspaceEdit(document_changes=[edit]))


@server.command("codeAction.moveSymbol")
def move_symbol_command(ls: LanguageServer, args):
    uri = cast(str, args[0])
    location = cast(
        dict[Literal["start", "end"], dict[Literal["line", "character"], int]], args[1]
    )
    LOGGER.debug("codeAction.moveSymbol: %s", args)
    for _, _, mod in server.get_mods(uri):
        move_source = move_symbol_source(
            mod, location["start"]["line"] + 1, location["start"]["character"]
        )
        print(move_source.symbol_name)
        server.add_move(uri, move_source)


@dataclass
class ProcessOutput:
    stdout: str
    stderr: str
    statuscode: int


def execute_ruff(args: Sequence[str], source: str) -> ProcessOutput:
    process = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    (out, err) = process.communicate(bytes(source, encoding="utf-8"))
    code = process.wait()
    return ProcessOutput(
        statuscode=code, stdout=bytes.decode(out), stderr=bytes.decode(err)
    )


def reformat_code(document_uri: str, source: str) -> str:
    # ruff check --stdin-filename "azsqdf.py" --fix --fix-only --select I --quiet
    # ruff format --stdin-filename "azsqdf.py"
    reformat_out = execute_ruff(
        [
            "ruff",
            "format",
            "--stdin-filename",
            document_uri,
        ],
        source,
    )
    return execute_ruff(
        [
            "ruff",
            "check",
            "--fix-only",
            "--quiet",
            "--select",
            "I",
            "--stdin-filename",
            document_uri,
        ],
        reformat_out.stdout,
    ).stdout


@server.command("codeAction.finishMoveSymbol")
def finish_move_symbol_command(ls: LanguageServer, args):
    uri = cast(str, args[0])
    location = cast(
        dict[Literal["start", "end"], dict[Literal["line", "character"], int]], args[1]
    )
    LOGGER.debug("codeAction.finishMoveSymbol: %s", args)
    mods = {workspace: (graph, mod) for workspace, graph, mod in server.get_mods(uri)}
    print(len(mods))
    for workspace, move in server.get_workspace_moves(uri):
        print(workspace, move.symbol_name)
        if workspace not in mods:
            continue
        graph, mod = mods[workspace]
        print(mod.full_mod_name)
        updated_mods = move_symbol_target(
            graph, mod, move, location["start"]["line"] + 1
        )
        print([m.full_mod_name for m in updated_mods])
        for mod in updated_mods:
            updated_code = reformat_code(mod.full_mod_name, mod.cst.code)
            document = ls.workspace.get_text_document(str(mod.url.resolve()))
            edit = TextDocumentEdit(
                text_document=OptionalVersionedTextDocumentIdentifier(
                    uri=f"file://{document.uri}", version=document.version
                ),
                edits=get_text_edits(document.source, updated_code),
            )
            ls.apply_edit(WorkspaceEdit(document_changes=[edit]))


@click.command("serve")
def serve():
    config = load_config()

    print(f"Start server at {config.server_url}:{config.server_port}")
    server.start_tcp(config.server_url, config.server_port)
