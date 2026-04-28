from __future__ import annotations

import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pyodbc

from .config import Settings
from .masking import mask_rows
from .sql_safety import validate_select_sql


class DatabaseError(RuntimeError):
    """Raised for database execution errors with safe public messages."""


@dataclass(frozen=True)
class ConnectionAttempt:
    settings: Settings
    reason: str


class SqlServerClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def server_info(self) -> dict[str, object]:
        return self.settings.public_dict()

    def list_schemas(self) -> dict[str, object]:
        return self._query(
            """
            SELECT name AS schema_name
            FROM sys.schemas
            WHERE principal_id IS NOT NULL
            ORDER BY name
            """,
            [],
            mask=False,
        )

    def list_tables(self, schema: str | None = None) -> dict[str, object]:
        params: list[Any] = []
        where = ""
        if schema:
            where = "WHERE s.name = ?"
            params.append(schema)
        return self._query(
            f"""
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                SUM(p.rows) AS estimated_rows,
                t.create_date,
                t.modify_date
            FROM sys.tables AS t
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            LEFT JOIN sys.partitions AS p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
            {where}
            GROUP BY s.name, t.name, t.create_date, t.modify_date
            ORDER BY s.name, t.name
            """,
            params,
            mask=False,
        )

    def describe_table(self, schema: str, table: str) -> dict[str, object]:
        return self._query(
            """
            SELECT
                c.column_id,
                c.name AS column_name,
                typ.name AS data_type,
                c.max_length,
                c.precision,
                c.scale,
                c.is_nullable,
                c.is_identity,
                dc.definition AS default_definition
            FROM sys.columns AS c
            INNER JOIN sys.types AS typ ON typ.user_type_id = c.user_type_id
            INNER JOIN sys.tables AS t ON t.object_id = c.object_id
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            LEFT JOIN sys.default_constraints AS dc
                ON dc.parent_object_id = c.object_id
                AND dc.parent_column_id = c.column_id
            WHERE s.name = ? AND t.name = ?
            ORDER BY c.column_id
            """,
            [schema, table],
            mask=False,
        )

    def search_columns(self, search: str) -> dict[str, object]:
        return self._query(
            """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                c.name AS column_name,
                typ.name AS data_type,
                c.is_nullable
            FROM sys.columns AS c
            INNER JOIN sys.tables AS t ON t.object_id = c.object_id
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            INNER JOIN sys.types AS typ ON typ.user_type_id = c.user_type_id
            WHERE c.name LIKE ?
            ORDER BY s.name, t.name, c.column_id
            """,
            [f"%{search}%"],
            mask=False,
        )

    def table_profile(self, schema: str, table: str) -> dict[str, object]:
        estimate = self._query(
            """
            SELECT SUM(p.rows) AS estimated_rows
            FROM sys.tables AS t
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            LEFT JOIN sys.partitions AS p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
            WHERE s.name = ? AND t.name = ?
            """,
            [schema, table],
            mask=False,
        )
        columns = self.describe_table(schema, table)
        return {
            "schema": schema,
            "table": table,
            "estimated_rows": estimate["rows"][0]["estimated_rows"] if estimate["rows"] else None,
            "columns": columns["rows"],
        }

    def index_info(self, schema: str, table: str) -> dict[str, object]:
        return self._query(
            """
            SELECT
                i.name AS index_name,
                i.type_desc,
                i.is_unique,
                i.is_primary_key,
                i.is_unique_constraint,
                c.name AS column_name,
                ic.key_ordinal,
                ic.is_included_column,
                ic.is_descending_key
            FROM sys.indexes AS i
            INNER JOIN sys.tables AS t ON t.object_id = i.object_id
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            LEFT JOIN sys.index_columns AS ic
                ON ic.object_id = i.object_id
                AND ic.index_id = i.index_id
            LEFT JOIN sys.columns AS c
                ON c.object_id = ic.object_id
                AND c.column_id = ic.column_id
            WHERE s.name = ? AND t.name = ? AND i.index_id > 0
            ORDER BY i.name, ic.key_ordinal, ic.index_column_id
            """,
            [schema, table],
            mask=False,
        )

    def foreign_keys(self, schema: str | None = None, table: str | None = None) -> dict[str, object]:
        params: list[Any] = []
        filters: list[str] = []
        if schema:
            filters.append("s.name = ?")
            params.append(schema)
        if table:
            filters.append("t.name = ?")
            params.append(table)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        return self._query(
            f"""
            SELECT
                fk.name AS foreign_key_name,
                s.name AS schema_name,
                t.name AS table_name,
                c.name AS column_name,
                rs.name AS referenced_schema_name,
                rt.name AS referenced_table_name,
                rc.name AS referenced_column_name,
                fk.delete_referential_action_desc,
                fk.update_referential_action_desc
            FROM sys.foreign_keys AS fk
            INNER JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id = fk.object_id
            INNER JOIN sys.tables AS t ON t.object_id = fk.parent_object_id
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            INNER JOIN sys.columns AS c
                ON c.object_id = fkc.parent_object_id
                AND c.column_id = fkc.parent_column_id
            INNER JOIN sys.tables AS rt ON rt.object_id = fk.referenced_object_id
            INNER JOIN sys.schemas AS rs ON rs.schema_id = rt.schema_id
            INNER JOIN sys.columns AS rc
                ON rc.object_id = fkc.referenced_object_id
                AND rc.column_id = fkc.referenced_column_id
            {where}
            ORDER BY s.name, t.name, fk.name, fkc.constraint_column_id
            """,
            params,
            mask=False,
        )

    def dependencies(self, schema: str, table: str) -> dict[str, object]:
        return self._query(
            """
            SELECT
                referencing_schema_name = OBJECT_SCHEMA_NAME(d.referencing_id),
                referencing_entity_name = OBJECT_NAME(d.referencing_id),
                o.type_desc AS referencing_type,
                d.referenced_schema_name,
                d.referenced_entity_name,
                d.referenced_minor_name
            FROM sys.sql_expression_dependencies AS d
            LEFT JOIN sys.objects AS o ON o.object_id = d.referencing_id
            WHERE
                (d.referenced_schema_name = ? AND d.referenced_entity_name = ?)
                OR (OBJECT_SCHEMA_NAME(d.referencing_id) = ? AND OBJECT_NAME(d.referencing_id) = ?)
            ORDER BY referencing_schema_name, referencing_entity_name
            """,
            [schema, table, schema, table],
            mask=False,
        )

    def sample_rows(
        self,
        schema: str,
        table: str,
        limit: int | None = None,
        mask: bool = True,
    ) -> dict[str, object]:
        row_limit = self._effective_limit(limit)
        quoted_table = f"{_quote_identifier(schema)}.{_quote_identifier(table)}"
        return self._query(
            f"SELECT TOP ({row_limit + 1}) * FROM {quoted_table}",
            [],
            requested_limit=row_limit,
            mask=mask,
        )

    def run_select(self, sql: str, limit: int | None = None, mask: bool = True) -> dict[str, object]:
        row_limit = self._effective_limit(limit)
        validated_sql = validate_select_sql(sql).sql
        return self._query(validated_sql, [], requested_limit=row_limit, mask=mask)

    def explain_select(self, sql: str) -> dict[str, object]:
        validated = validate_select_sql(sql).sql
        started = time.perf_counter()
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute("SET SHOWPLAN_XML ON")
                try:
                    cursor.execute(validated)
                    rows = cursor.fetchall()
                    plans = [row[0] for row in rows if row and row[0] is not None]
                finally:
                    cursor.execute("SET SHOWPLAN_XML OFF")
        except pyodbc.Error as exc:
            raise DatabaseError(_safe_db_error(exc)) from exc
        return {
            "elapsed_ms": _elapsed_ms(started),
            "plan_count": len(plans),
            "plans": plans,
        }

    def _query(
        self,
        sql: str,
        params: Sequence[Any],
        *,
        requested_limit: int | None = None,
        mask: bool,
    ) -> dict[str, object]:
        started = time.perf_counter()
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, list(params))
                rows = (
                    cursor.fetchmany(requested_limit + 1)
                    if requested_limit is not None
                    else cursor.fetchall()
                )
                columns = _cursor_columns(cursor.description or [])
        except pyodbc.Error as exc:
            raise DatabaseError(_safe_db_error(exc)) from exc

        serialized_rows = [_row_to_dict(columns, row) for row in rows]
        truncated = False
        if requested_limit is not None and len(serialized_rows) > requested_limit:
            serialized_rows = serialized_rows[:requested_limit]
            truncated = True
        serialized_rows = mask_rows(serialized_rows, enabled=mask)
        return {
            "elapsed_ms": _elapsed_ms(started),
            "row_count": len(serialized_rows),
            "truncated": truncated,
            "columns": columns,
            "rows": serialized_rows,
        }

    def _connect(self) -> pyodbc.Connection:
        errors: list[str] = []
        for attempt in _connection_attempts(self.settings):
            try:
                return pyodbc.connect(
                    attempt.settings.connection_string(),
                    autocommit=True,
                    timeout=attempt.settings.timeout_seconds,
                )
            except pyodbc.Error as exc:
                errors.append(f"{attempt.reason}: {_safe_db_error(exc)}")
        raise DatabaseError(" | ".join(errors))

    def _effective_limit(self, limit: int | None) -> int:
        if limit is None:
            return self.settings.max_rows
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        return min(limit, self.settings.max_rows)


def _quote_identifier(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("Identifier cannot be empty or contain NUL bytes.")
    return "[" + value.replace("]", "]]") + "]"


def _cursor_columns(description: Iterable[Any]) -> list[str]:
    return [item[0] for item in description]


def _row_to_dict(columns: list[str], row: Any) -> dict[str, Any]:
    return {
        column: _serialize_value(value)
        for column, value in zip(columns, row, strict=False)
    }


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def _safe_db_error(exc: pyodbc.Error) -> str:
    text = str(exc)
    for marker in ("PWD=", "Password=", "UID="):
        if marker in text:
            return "Database operation failed. Check server permissions and connectivity."
    return text


def _connection_attempts(settings: Settings) -> list[ConnectionAttempt]:
    attempts = [ConnectionAttempt(settings, "configured connection")]
    seen = {(settings.server, settings.driver, settings.encrypt)}

    if settings.auth == "windows" and _looks_local_server(settings.server):
        fallback_specs = [
            (settings.driver, "no", "local Windows auth fallback with Encrypt=no"),
            ("ODBC Driver 17 for SQL Server", "no", "ODBC Driver 17 fallback"),
            ("SQL Server", "no", "legacy SQL Server ODBC fallback"),
        ]
        for driver, encrypt, reason in fallback_specs:
            key = (settings.server, driver, encrypt)
            if key in seen:
                continue
            seen.add(key)
            attempts.append(
                ConnectionAttempt(
                    settings.with_overrides(driver=driver, encrypt=encrypt),
                    reason,
                )
            )
    return attempts


def _looks_local_server(server: str) -> bool:
    normalized = server.strip().lower()
    return normalized.startswith("localhost") or normalized.startswith("(local)") or normalized.startswith(".\\")


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
