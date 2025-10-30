from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional, Literal, Dict, Any

class VizSpec(BaseModel):
    type: Literal["line", "bar", "table"]
    x: Optional[Literal["date", "category", "region", "store", "sku"]] = None
    y: Optional[List[str]] = None
    groupBy: Optional[List[Literal["date", "region", "category", "store", "sku"]]] = None
    aggregation: Optional[Literal["sum", "avg", "count"]] = None
    explanations: Optional[List[str]] = None
    
    @field_validator('x', mode='before')
    @classmethod
    def validate_x(cls, v):
        # Convert empty strings to None to satisfy Optional[Literal[...]]
        if v == '' or v is None:
            return None
        return v
    
    @field_validator('y', mode='before')
    @classmethod
    def validate_y(cls, v):
        # Handle empty lists or None
        if v is None or (isinstance(v, list) and len(v) == 0):
            return None
        return v
    
    @field_validator('groupBy', mode='before')
    @classmethod
    def validate_group_by(cls, v):
        # Handle empty lists or None
        if v is None or (isinstance(v, list) and len(v) == 0):
            return None
        return v

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

