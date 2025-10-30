import duckdb
from typing import List, Dict, Any
import os
from ..settings import Settings

class DuckDBDriver:
    def __init__(self, settings: Settings) -> None:
        db_path = os.path.join(os.getcwd(), "duckdb.db")
        self.conn = duckdb.connect(db_path)
        # Ensure table exists (seed script populates data)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS retail_sales (
              date DATE,
              store_id VARCHAR,
              store_name VARCHAR,
              region VARCHAR,
              category VARCHAR,
              sku VARCHAR,
              units INTEGER,
              net_sales DECIMAL(12,2)
            )
            """
        )

    def query(self, sql: str) -> List[Dict[str, Any]]:
        res = self.conn.execute(sql)
        cols = [c[0] for c in res.description]
        rows = res.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def infer_schema(self, rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        if not rows:
            return []
        schema: List[Dict[str, str]] = []
        sample = rows[0]
        for k, v in sample.items():
            t = type(v).__name__
            schema.append({"name": k, "type": t})
        return schema

