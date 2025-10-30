from typing import List, Dict, Any
from clickhouse_driver import Client
from ..settings import Settings
from urllib.parse import urlparse

class ClickHouseDriver:
    def __init__(self, settings: Settings) -> None:
        parsed = urlparse(settings.clickhouse_url)
        host = parsed.hostname or "localhost"
        # ClickHouse native protocol uses port 9000, HTTP uses 8123
        # clickhouse-driver needs native protocol port
        port = parsed.port if parsed.port and parsed.port != 8123 else 9000
        self.client = Client(host=host, port=port, settings={"strings_as_nullable": True})
        self._ensure_table()

    def _ensure_table(self):
        # Simple MergeTree table compatible with our schema
        self.client.execute(
            """
            CREATE TABLE IF NOT EXISTS retail_sales (
              date Date,
              store_id String,
              store_name String,
              region String,
              category String,
              sku String,
              units Int32,
              net_sales Decimal(12,2)
            ) ENGINE = MergeTree ORDER BY (date, store_id)
            """
        )

    def query(self, sql: str) -> List[Dict[str, Any]]:
        data, columns = self.client.execute(sql, with_column_types=True)
        col_names = [c[0] for c in columns]
        return [dict(zip(col_names, row)) for row in data]

    def infer_schema(self, rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        if not rows:
            return []
        sample = rows[0]
        return [{"name": k, "type": type(v).__name__} for k, v in sample.items()]

