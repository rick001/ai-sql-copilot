from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Literal, Dict, Any

class VizSpec(BaseModel):
    type: Literal["line", "bar", "table"]
    x: Optional[Literal["date", "category", "region", "store", "sku"]] = None
    y: Optional[List[str]] = None
    groupBy: Optional[List[Literal["date", "region", "category", "store", "sku"]]] = None
    aggregation: Optional[Literal["sum", "avg", "count"]] = None
    explanations: Optional[List[str]] = None

class ModelEnvelope(BaseModel):
    answer: str
    sql: Optional[str] = None
    viz: Optional[VizSpec] = None

class ColumnSchema(BaseModel):
    name: str
    type: str

class QueryResult(BaseModel):
    columns: List[ColumnSchema]
    rows: List[Dict[str, Any]]

class ChatPayload(BaseModel):
    answer: str
    sql: Optional[str] = None
    viz: Optional[VizSpec] = None
    rows: Optional[List[Dict[str, Any]]] = None
    schema: Optional[List[ColumnSchema]] = None

