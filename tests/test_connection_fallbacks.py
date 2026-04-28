from mcp_sql_server.config import Settings
from mcp_sql_server.db import _connection_attempts


def test_local_windows_auth_adds_fallback_attempts():
    settings = Settings(
        server=r"localhost\SQLEXPRESS",
        auth="windows",
        driver="ODBC Driver 18 for SQL Server",
        encrypt="yes",
    )

    attempts = _connection_attempts(settings)

    assert [attempt.reason for attempt in attempts] == [
        "configured connection",
        "local Windows auth fallback with Encrypt=no",
        "ODBC Driver 17 fallback",
        "legacy SQL Server ODBC fallback",
    ]
    assert attempts[1].settings.encrypt == "no"
    assert attempts[2].settings.driver == "ODBC Driver 17 for SQL Server"
    assert attempts[3].settings.driver == "SQL Server"


def test_remote_or_sql_auth_does_not_add_fallback_attempts():
    remote = Settings(server="prod-sql", auth="windows")
    sql_auth = Settings(server=r"localhost\SQLEXPRESS", auth="sql", username="u", password="p")

    assert len(_connection_attempts(remote)) == 1
    assert len(_connection_attempts(sql_auth)) == 1
