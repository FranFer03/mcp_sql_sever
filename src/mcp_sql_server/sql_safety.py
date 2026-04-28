from __future__ import annotations

import re
from dataclasses import dataclass


class UnsafeSqlError(ValueError):
    """Raised when a SQL statement is outside the read-only policy."""


FORBIDDEN_KEYWORDS = {
    "ALTER",
    "BACKUP",
    "BULK",
    "CREATE",
    "DELETE",
    "DROP",
    "EXEC",
    "EXECUTE",
    "INSERT",
    "MERGE",
    "RESTORE",
    "TRUNCATE",
    "UPDATE",
    "USE",
}

SELECT_INTO_PATTERN = re.compile(r"\bINTO\b", re.IGNORECASE)


@dataclass(frozen=True)
class ValidatedSql:
    sql: str


def validate_select_sql(sql: str) -> ValidatedSql:
    cleaned = sql.strip()
    if not cleaned:
        raise UnsafeSqlError("SQL is empty.")
    if "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise UnsafeSqlError("SQL comments are not allowed in ad hoc queries.")

    scanned = _scan(cleaned)
    statement = scanned.sql_without_trailing_semicolon.strip()
    if scanned.statement_separator_count > 1 or scanned.has_non_trailing_separator:
        raise UnsafeSqlError("Only one SQL statement is allowed.")
    if not statement:
        raise UnsafeSqlError("SQL is empty.")

    first = _first_keyword(statement)
    if first not in {"SELECT", "WITH"}:
        raise UnsafeSqlError("Only SELECT statements and CTEs are allowed.")

    forbidden = FORBIDDEN_KEYWORDS.intersection(_keywords(statement))
    if forbidden:
        raise UnsafeSqlError(f"Forbidden SQL keyword: {sorted(forbidden)[0]}.")
    if SELECT_INTO_PATTERN.search(statement):
        raise UnsafeSqlError("SELECT INTO is not allowed.")

    return ValidatedSql(sql=statement)


def limit_select_sql(sql: str, max_rows: int) -> str:
    validated = validate_select_sql(sql).sql
    return f"SELECT TOP ({max_rows + 1}) * FROM ({validated}) AS mcp_limited_result"


@dataclass(frozen=True)
class _ScanResult:
    sql_without_trailing_semicolon: str
    statement_separator_count: int
    has_non_trailing_separator: bool


def _scan(sql: str) -> _ScanResult:
    in_single_quote = False
    separators = 0
    separator_indexes: list[int] = []
    last_non_space_index = -1

    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'":
            if in_single_quote and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_single_quote = not in_single_quote
        elif char == ";" and not in_single_quote:
            separators += 1
            separator_indexes.append(i)
        if not char.isspace():
            last_non_space_index = i
        i += 1

    if in_single_quote:
        raise UnsafeSqlError("SQL string literal is not closed.")

    sql_without_trailing_semicolon = sql
    trailing_semicolon_index = -1
    if last_non_space_index >= 0 and sql[last_non_space_index] == ";":
        trailing_semicolon_index = last_non_space_index
        sql_without_trailing_semicolon = sql[:last_non_space_index]

    has_non_trailing_separator = any(
        index != trailing_semicolon_index for index in separator_indexes
    )

    return _ScanResult(sql_without_trailing_semicolon, separators, has_non_trailing_separator)


def _first_keyword(sql: str) -> str:
    match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)", sql)
    return match.group(1).upper() if match else ""


def _keywords(sql: str) -> set[str]:
    scrubbed = _replace_string_literals(sql)
    return {token.upper() for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", scrubbed)}


def _replace_string_literals(sql: str) -> str:
    result: list[str] = []
    in_single_quote = False
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'":
            if in_single_quote and i + 1 < len(sql) and sql[i + 1] == "'":
                result.append(" ")
                result.append(" ")
                i += 2
                continue
            in_single_quote = not in_single_quote
            result.append(" ")
        elif in_single_quote:
            result.append(" ")
        else:
            result.append(char)
        i += 1
    return "".join(result)
