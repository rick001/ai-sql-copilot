from typing import Any, Dict
from decimal import Decimal
from datetime import date, datetime
from .sql_validator import validate_sql
from .sql_translator import translate_to_clickhouse
from .db.repository import Repository

def json_serialize(obj):
    """Convert non-JSON types to JSON-compatible types"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: json_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_serialize(item) for item in obj]
    return obj

class ToolRunner:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def run(self, name: str, input_json: Dict[str, Any]) -> Dict[str, Any]:
        if name != "query_sql":
            return {"error": f"Unknown tool {name}"}
        sql = input_json.get("sql", "").strip()
        
        # Check for incomplete SQL patterns
        if not sql or sql == "SELECT" or sql.startswith("SELECT ...") or "..." in sql:
            return {
                "error": "SQL query is incomplete. Please provide a complete SELECT statement with FROM clause. Example: SELECT column FROM retail_sales WHERE condition",
                "hint": "The SQL must include: SELECT, FROM retail_sales, and optionally WHERE/GROUP BY/ORDER BY clauses. Do not use '...' or incomplete statements."
            }
        
        # Remove trailing semicolon if present (common in generated SQL)
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        
        # Translate SQL to ClickHouse-compatible syntax BEFORE validation
        sql = translate_to_clickhouse(sql)
        
        ok, msg = validate_sql(sql)
        if not ok:
            # Provide helpful hints for common errors
            hint = ""
            if "Missing FROM clause" in msg:
                hint = " Add 'FROM retail_sales' to your SELECT statement."
            elif "forbidden tokens" in msg.lower():
                hint = " Remove semicolons, comments (--, /* */), or DDL/DML keywords from your SQL."
            elif "Only SELECT" in msg:
                hint = " Only SELECT queries are allowed. Use SELECT statements only."
            
            return {
                "error": f"{msg}.{hint}",
                "hint": f"Valid SQL format: SELECT columns FROM retail_sales [WHERE conditions] [GROUP BY columns] [ORDER BY columns]. Your SQL: {sql[:100]}"
            }
        
        try:
            rows = self.repo.query(sql)
        except Exception as db_error:
            error_msg = str(db_error)
            # Provide database-specific hints
            hint = ""
            if "Unknown expression" in error_msg or "function" in error_msg.lower():
                hint = " Check that all functions and syntax are compatible with the database. Use standard SQL functions."
            elif "table" in error_msg.lower() and "does not exist" in error_msg.lower():
                hint = " Only use the 'retail_sales' table. No other tables exist."
            
            return {
                "error": f"Database error: {error_msg[:200]}.{hint}",
                "hint": f"Try simplifying your SQL query. Available columns: date, store_id, store_name, region, category, sku, units, net_sales"
            }
        
        schema = self.repo.infer_schema(rows)
        # Convert Decimal and other types to JSON-serializable
        serialized_rows = json_serialize(rows[:5000])
        serialized_schema = json_serialize(schema)
        return {"rows": serialized_rows, "schema": serialized_schema}

