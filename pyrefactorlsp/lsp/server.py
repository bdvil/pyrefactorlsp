from pygls.server import LanguageServer


def serve():
    server = LanguageServer('example-server', 'v0.1')
