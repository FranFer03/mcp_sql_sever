from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import ConfigError, Settings
from .db import DatabaseError, SqlServerClient
from .sql_safety import UnsafeSqlError


INSTRUCTIONS = """
Read-only SQL Server investigator for one fixed database.
Use schema and profiling tools before running ad hoc SELECT statements.
Ad hoc SQL accepts only one SELECT/CTE statement and results are capped.
"""

mcp = FastMCP("SQL Server Read-Only Investigator", instructions=INSTRUCTIONS)


def _client() -> SqlServerClient:
    return SqlServerClient(Settings.from_env())


def _public_error(exc: Exception) -> dict[str, object]:
    return {"error": type(exc).__name__, "message": str(exc)}


@mcp.tool()
def server_info() -> dict[str, object]:
    """Return SQL Server MCP configuration without exposing secrets."""
    try:
        return _client().server_info()
    except ConfigError as exc:
        return _public_error(exc)


@mcp.tool()
def list_schemas() -> dict[str, object]:
    """List visible schemas in the configured database."""
    try:
        return _client().list_schemas()
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def list_tables(schema: str | None = None) -> dict[str, object]:
    """List visible user tables, optionally within one schema."""
    try:
        return _client().list_tables(schema)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def describe_table(schema: str, table: str) -> dict[str, object]:
    """Describe columns and defaults for a table."""
    try:
        return _client().describe_table(schema, table)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def search_columns(search: str) -> dict[str, object]:
    """Search visible table columns by partial column name."""
    try:
        return _client().search_columns(search)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def table_profile(schema: str, table: str) -> dict[str, object]:
    """Return estimated row count and column metadata for a table."""
    try:
        return _client().table_profile(schema, table)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def index_info(schema: str, table: str) -> dict[str, object]:
    """List indexes and indexed columns for a table."""
    try:
        return _client().index_info(schema, table)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def foreign_keys(schema: str | None = None, table: str | None = None) -> dict[str, object]:
    """List foreign keys, optionally filtered by table."""
    try:
        return _client().foreign_keys(schema, table)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def dependencies(schema: str, table: str) -> dict[str, object]:
    """List SQL expression dependencies involving a table."""
    try:
        return _client().dependencies(schema, table)
    except (ConfigError, DatabaseError) as exc:
        return _public_error(exc)


@mcp.tool()
def sample_rows(
    schema: str,
    table: str,
    limit: int | None = None,
    mask_sensitive: bool = True,
) -> dict[str, object]:
    """Return capped sample rows from a table, masking sensitive columns by default."""
    try:
        return _client().sample_rows(schema, table, limit, mask_sensitive)
    except (ConfigError, DatabaseError, ValueError) as exc:
        return _public_error(exc)


@mcp.tool()
def run_select(sql: str, limit: int | None = None, mask_sensitive: bool = True) -> dict[str, object]:
    """Run one capped read-only SELECT or CTE query."""
    try:
        return _client().run_select(sql, limit, mask_sensitive)
    except (ConfigError, DatabaseError, UnsafeSqlError, ValueError) as exc:
        return _public_error(exc)


@mcp.tool()
def explain_select(sql: str) -> dict[str, object]:
    """Return estimated SHOWPLAN XML for one read-only SELECT or CTE query."""
    try:
        return _client().explain_select(sql)
    except (ConfigError, DatabaseError, UnsafeSqlError) as exc:
        return _public_error(exc)


def main() -> None:
    mcp.run(transport="stdio")
