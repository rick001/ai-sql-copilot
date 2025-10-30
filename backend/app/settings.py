from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Literal, Optional, Union

class Settings(BaseSettings):
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_model_id: str = Field(default="anthropic.claude-3-5-sonnet-20240620-v1:0", alias="BEDROCK_MODEL_ID")
    db_driver: Literal["duckdb", "clickhouse"] = Field(default="duckdb", alias="DB_DRIVER")
    clickhouse_url: str = Field(default="http://localhost:8123", alias="CLICKHOUSE_URL")
    bedrock_mock: int = Field(default=1, alias="BEDROCK_MOCK")
    # Ollama settings
    use_ollama: int = Field(default=0, alias="USE_OLLAMA")  # 1 to use Ollama instead of Bedrock
    ollama_url: Optional[str] = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: Optional[str] = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")

    @field_validator('use_ollama', mode='before')
    @classmethod
    def parse_use_ollama(cls, v):
        if v == '' or v is None:
            return 0
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return int(v)

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

