import os

import pytest

from mcp_sql_server.config import Settings
from mcp_sql_server.db import SqlServerClient


@pytest.mark.skipif(
    not os.getenv("MSSQL_TEST_SERVER"),
    reason="Set MSSQL_TEST_SERVER and related env vars to run SQL Server integration tests.",
)
def test_integration_server_info(monkeypatch):
    monkeypatch.setenv("MSSQL_SERVER", os.environ["MSSQL_TEST_SERVER"])
    monkeypatch.setenv("MSSQL_DATABASE", os.environ["MSSQL_TEST_DATABASE"])
    monkeypatch.setenv("MSSQL_USERNAME", os.environ["MSSQL_TEST_USERNAME"])
    monkeypatch.setenv("MSSQL_PASSWORD", os.environ["MSSQL_TEST_PASSWORD"])

    client = SqlServerClient(Settings.from_env())
    info = client.server_info()

    assert info["server"] == os.environ["MSSQL_TEST_SERVER"]
    assert info["database"] == os.environ["MSSQL_TEST_DATABASE"]
