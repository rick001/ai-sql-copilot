from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional, Literal, Dict, Any

class VizSpec(BaseModel):
    type: Literal["line", "bar", "table"]
    x: Optional[Literal["date", "category", "region", "store", "store_name", "sku"]] = None
    y: Optional[List[str]] = None
    groupBy: Optional[List[Literal["date", "region", "category", "store", "store_name", "store_id", "sku"]]] = None
    aggregation: Optional[Literal["sum", "avg", "count"]] = None
    explanations: Optional[List[str]] = None
    
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
        # Normalize store_name and store_id to 'store' for consistency
        # Filter out time aggregations (month, year, quarter, etc.) - these are not column names
        if isinstance(v, list):
            normalized = []
            time_aggregations = {'month', 'year', 'quarter', 'week', 'day'}
            for item in v:
                if not item:
                    continue
                # Filter out time aggregations - they're not actual columns
                if isinstance(item, str) and item.lower() in time_aggregations:
                    continue  # Skip time aggregations in groupBy
                if item in ('store_name', 'store_id'):
                    normalized.append('store')
                else:
                    normalized.append(item)
            # Return None if list becomes empty, otherwise return normalized list
            return normalized if len(normalized) > 0 else None
        return v
    
    @field_validator('x', mode='before')
    @classmethod
    def validate_x(cls, v):
        # Convert empty strings to None to satisfy Optional[Literal[...]]
        if v == '' or v is None:
            return None
        # Normalize store_name and store_id to 'store'
        if v in ('store_name', 'store_id'):
            return 'store'
        # Normalize time aggregations to 'date' (month, year, quarter, etc. are not columns)
        if v and isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ('month', 'year', 'quarter', 'week', 'day', 'date'):
                return 'date'
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

