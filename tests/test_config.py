import pytest

from mcp_sql_server.config import ConfigError, Settings


def test_settings_from_env_requires_core_values(monkeypatch):
    monkeypatch.setenv("MSSQL_AUTH", "sql")
    monkeypatch.delenv("MSSQL_SERVER", raising=False)
    monkeypatch.delenv("MSSQL_DATABASE", raising=False)
    monkeypatch.delenv("MSSQL_USERNAME", raising=False)
    monkeypatch.delenv("MSSQL_PASSWORD", raising=False)
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_connection_string_contains_read_only_intent_without_public_secret():
    settings = Settings(
        server="localhost",
        database="Replica",
        username="readonly@example.com",
        password="super-secret",
    )
    connection_string = settings.connection_string()
    public = settings.public_dict()

    assert "ApplicationIntent=ReadOnly" in connection_string
    assert "PWD=super-secret" in connection_string
    assert "super-secret" not in str(public)
    assert public["username"] == "r***@example.com"


def test_windows_auth_connection_string_uses_trusted_connection():
    settings = Settings(
        server=r"localhost\SQLEXPRESS",
        auth="windows",
        encrypt="yes",
        trust_server_certificate="yes",
    )
    connection_string = settings.connection_string()
    public = settings.public_dict()

    assert r"SERVER=localhost\SQLEXPRESS" in connection_string
    assert "Trusted_Connection=yes" in connection_string
    assert "UID=" not in connection_string
    assert "PWD=" not in connection_string
    assert "DATABASE=" not in connection_string
    assert public["database"] == "<default>"
    assert public["username"] == "<windows>"


def test_encrypt_aliases_are_normalized():
    settings = Settings(
        server=r"localhost\SQLEXPRESS",
        auth="windows",
        encrypt="no",
    )
    assert settings.with_overrides(encrypt="Mandatory").encrypt == "yes"
    assert settings.with_overrides(encrypt="Optional").encrypt == "no"


def test_env_limits_are_validated(monkeypatch):
    monkeypatch.setenv("MSSQL_AUTH", "sql")
    monkeypatch.setenv("MSSQL_SERVER", "server")
    monkeypatch.setenv("MSSQL_DATABASE", "db")
    monkeypatch.setenv("MSSQL_USERNAME", "user")
    monkeypatch.setenv("MSSQL_PASSWORD", "pass")
    monkeypatch.setenv("MCP_SQL_MAX_ROWS", "0")
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_invalid_encrypt_value_is_rejected(monkeypatch):
    monkeypatch.setenv("MSSQL_SERVER", "server")
    monkeypatch.setenv("MSSQL_AUTH", "windows")
    monkeypatch.setenv("MSSQL_ENCRYPT", "maybe")
    with pytest.raises(ConfigError):
        Settings.from_env()
