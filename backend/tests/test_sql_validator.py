import pytest
from app.sql_validator import validate_sql


def test_rejects_ddl():
    ok, msg = validate_sql("DROP TABLE retail_sales")
    assert not ok


def test_requires_select():
    ok, _ = validate_sql("UPDATE retail_sales SET units=0")
    assert not ok


def test_enforces_table():
    ok, _ = validate_sql("SELECT * FROM other_table")
    assert not ok


def test_allows_simple_select():
    ok, _ = validate_sql("SELECT date, region, sum(net_sales) as net_sales FROM retail_sales GROUP BY date, region")
    assert ok

