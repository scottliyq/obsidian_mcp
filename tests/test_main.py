from pathlib import Path
from types import SimpleNamespace

from app import main as main_module


class FakeServer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def _fake_config(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
    stateless_http: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        server=SimpleNamespace(
            transport=transport,
            host=host,
            port=port,
            path=path,
            stateless_http=stateless_http,
        )
    )


def test_main_run_stdio(monkeypatch) -> None:
    fake_server = FakeServer()

    monkeypatch.setattr(main_module, "load_config", lambda _: _fake_config(transport="stdio"))
    monkeypatch.setattr(main_module, "create_server", lambda _: fake_server)
    monkeypatch.setattr(
        "sys.argv",
        ["obsidian-mcp", "--config", "config.yaml", "--transport", "stdio"],
    )

    main_module.main()

    assert len(fake_server.calls) == 1
    assert fake_server.calls[0] == {"transport": "stdio"}


def test_main_run_streamable_http(monkeypatch, tmp_path: Path) -> None:
    fake_server = FakeServer()
    config_file = tmp_path / "config.yaml"

    def _create_server(config_path: Path) -> FakeServer:
        assert config_path == config_file
        return fake_server

    monkeypatch.setattr(main_module, "load_config", lambda _: _fake_config(transport="stdio"))
    monkeypatch.setattr(main_module, "create_server", _create_server)
    monkeypatch.setattr(
        "sys.argv",
        [
            "obsidian-mcp",
            "--config",
            str(config_file),
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--path",
            "/mcp",
            "--stateless-http",
        ],
    )

    main_module.main()

    assert len(fake_server.calls) == 1
    assert fake_server.calls[0] == {
        "transport": "streamable-http",
        "host": "0.0.0.0",
        "port": 9000,
        "path": "/mcp",
        "stateless_http": True,
    }


def test_main_run_streamable_http_from_config(monkeypatch) -> None:
    fake_server = FakeServer()

    monkeypatch.setattr(
        main_module,
        "load_config",
        lambda _: _fake_config(
            transport="streamable-http",
            host="0.0.0.0",
            port=9100,
            path="/custom",
            stateless_http=True,
        ),
    )
    monkeypatch.setattr(main_module, "create_server", lambda _: fake_server)
    monkeypatch.setattr("sys.argv", ["obsidian-mcp", "--config", "config.yaml"])

    main_module.main()

    assert len(fake_server.calls) == 1
    assert fake_server.calls[0] == {
        "transport": "streamable-http",
        "host": "0.0.0.0",
        "port": 9100,
        "path": "/custom",
        "stateless_http": True,
    }
