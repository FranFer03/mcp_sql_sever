from mcp_sql_server.db import _quote_identifier


def test_quote_identifier_escapes_closing_brackets():
    assert _quote_identifier("abc]def") == "[abc]]def]"
