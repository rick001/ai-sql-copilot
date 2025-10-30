from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..settings import Settings
from .duckdb_driver import DuckDBDriver
from .clickhouse_driver_impl import ClickHouseDriver

class Repository(ABC):
    @abstractmethod
    def query(self, sql: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def infer_schema(self, rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        ...

def get_repository(settings: Settings) -> Repository:
    if settings.db_driver == "clickhouse":
        return ClickHouseDriver(settings)
    return DuckDBDriver(settings)

