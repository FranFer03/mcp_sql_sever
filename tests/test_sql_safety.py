import pytest

from mcp_sql_server.sql_safety import UnsafeSqlError, limit_select_sql, validate_select_sql


@pytest.mark.parametrize(
    "sql",
    [
        "select 1",
        "SELECT * FROM dbo.Customers",
        "WITH cte AS (SELECT 1 AS value) SELECT value FROM cte",
        "SELECT ';' AS literal;",
    ],
)
def test_allows_read_only_selects(sql):
    assert validate_select_sql(sql).sql


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE dbo.Users SET Name = 'x'",
        "DELETE FROM dbo.Users",
        "INSERT INTO dbo.Users(Name) VALUES ('x')",
        "DROP TABLE dbo.Users",
        "EXEC dbo.DoSomething",
        "USE master SELECT 1",
        "SELECT 1; SELECT 2",
        "SELECT * INTO #tmp FROM dbo.Users",
        "SELECT * INTO dbo.Copy FROM dbo.Users",
        "SELECT 1 -- hidden",
        "SELECT /* hidden */ 1",
    ],
)
def test_blocks_unsafe_sql(sql):
    with pytest.raises(UnsafeSqlError):
        validate_select_sql(sql)


def test_limit_wraps_valid_sql():
    wrapped = limit_select_sql("SELECT id FROM dbo.Users", 25)
    assert wrapped == "SELECT TOP (26) * FROM (SELECT id FROM dbo.Users) AS mcp_limited_result"
