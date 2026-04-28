from mcp_sql_server.masking import is_sensitive_column, mask_row, mask_value


def test_detects_sensitive_column_names():
    assert is_sensitive_column("customer_email")
    assert is_sensitive_column("telefono")
    assert is_sensitive_column("api_token")
    assert not is_sensitive_column("created_at")


def test_masks_sensitive_values_only():
    row = {
        "customer_email": "person@example.com",
        "amount": 123,
        "token": "abcd",
    }
    assert mask_row(row) == {
        "customer_email": "pe***om",
        "amount": 123,
        "token": "***",
    }


def test_masking_can_be_disabled():
    row = {"email": "person@example.com"}
    assert mask_row(row, enabled=False) == row


def test_mask_value_handles_nulls():
    assert mask_value(None) is None
