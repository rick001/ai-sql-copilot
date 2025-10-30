from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
import os

from .settings import Settings
from .bedrock_client import BedrockClient
from .ollama_client import OllamaClient
from .db.repository import get_repository
from .tool_runner import ToolRunner
from .schemas import ModelEnvelope, VizSpec, ChatPayload, ColumnSchema
from .sql_validator import validate_sql
from .sql_translator import translate_to_clickhouse, validate_clickhouse_compatibility
import re

settings = Settings()

app = FastAPI(title="Analytics Copilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    role: Optional[Literal["manager", "analyst"]] = None


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatPayload)
async def chat(req: ChatRequest):
    repo = get_repository(settings)
    tool_runner = ToolRunner(repo)

    # Use Ollama if configured, otherwise Bedrock
    if settings.use_ollama == 1:
        client = OllamaClient(settings)
    else:
        client = BedrockClient(settings)

    system_prompt = client.load_system_prompt()

    # Enhance user message to emphasize key dimensions
    enhanced_message = req.message
    # If user mentions specific dimensions, reinforce them
    if "categor" in req.message.lower() and "region" not in req.message.lower():
        enhanced_message = f"{req.message} IMPORTANT: Use the category column, NOT region."
    elif "region" in req.message.lower() and "categor" not in req.message.lower():
        enhanced_message = f"{req.message} IMPORTANT: Use the region column."
    
    messages = [
        {"role": "user", "content": enhanced_message}
    ]

    tools = [
        {
            "toolSpec": {
                "name": "query_sql",
                "description": "Execute a validated SELECT query over retail_sales table. IMPORTANT: The SQL query must be COMPLETE and valid. It MUST include: SELECT columns FROM retail_sales [optional clauses]. Never use '...' or placeholders. The table has columns: date, store_id, store_name, region, category, sku, units, net_sales. When the user asks about 'categories', use the category column. When they ask about 'regions', use the region column. Always match the exact dimension the user specifies.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "A complete, valid SQL SELECT query. Must include SELECT, FROM retail_sales, and any necessary WHERE/GROUP BY/ORDER BY clauses. Do not use '...' or incomplete statements."
                            }
                        },
                        "required": ["sql"],
                    }
                },
            }
        }
    ]

    try:
        envelope = await client.converse(system_prompt=system_prompt, messages=messages, tools=tools, tool_runner=tool_runner)
    except Exception as e:
        error_msg = str(e)
        # Provide helpful guidance for common errors
        if "AccessDeniedException" in error_msg or "not authorized" in error_msg:
            help_text = (
                f"AWS IAM Permission Error: {error_msg}\n\n"
                "Your AWS user/role needs bedrock:InvokeModel permission.\n\n"
                "To fix:\n"
                "1. Go to IAM → Users → [Your User] → Add permissions\n"
                "2. Attach policy: AmazonBedrockFullAccess (or create custom policy with bedrock:InvokeModel)\n"
                "3. Or add this to your IAM policy:\n"
                '   {\n     "Effect": "Allow",\n     "Action": "bedrock:InvokeModel",\n     "Resource": "*"\n   }'
            )
            return ChatPayload(answer=help_text)
        elif "model identifier is invalid" in error_msg or "ValidationException" in error_msg:
            help_text = (
                f"Model ID error: {error_msg}\n\n"
                "To fix:\n"
                "1. Verify the model is available in AWS Bedrock Console\n"
                "2. Check your model ID in .env: " + settings.bedrock_model_id + "\n"
                "3. Ensure region matches: " + settings.aws_region
            )
            return ChatPayload(answer=help_text)
        model_type = "Ollama" if settings.use_ollama == 1 else "Bedrock"
        return ChatPayload(answer=f"{model_type} error: {error_msg}")

    try:
        parsed = ModelEnvelope.model_validate(envelope)
    except Exception as e:
        return ChatPayload(answer=f"Invalid model response: {e}")

    # Post-process SQL to fix common issues and translate to ClickHouse syntax
    if parsed.sql:
        # Apply comprehensive SQL translation for ClickHouse compatibility
        translated_sql = translate_to_clickhouse(parsed.sql)
        
        # Validate ClickHouse compatibility
        compatible, compat_msg = validate_clickhouse_compatibility(translated_sql)
        if not compatible:
            # Log warning but still use translated SQL (might work with further fixes)
            pass
        
        parsed.sql = translated_sql
    
    # 2. Fix dimension mismatches (categories vs regions)
    user_asked_category = "categor" in req.message.lower() and "region" not in req.message.lower()
    user_asked_region = "region" in req.message.lower() and "categor" not in req.message.lower()
    
    if parsed.sql and (user_asked_category or user_asked_region):
        sql_lower = parsed.sql.lower()
        if user_asked_category and "region" in sql_lower and "category" not in sql_lower:
            # Replace region with category in SQL
            corrected_sql = parsed.sql.replace("region", "category").replace("REGION", "category")
            parsed.sql = corrected_sql
            if parsed.viz and parsed.viz.groupBy:
                parsed.viz.groupBy = [g if g != "region" else "category" for g in parsed.viz.groupBy]
            if parsed.viz and parsed.viz.x == "region":
                parsed.viz.x = "category"
        elif user_asked_region and "category" in sql_lower and "region" not in sql_lower:
            # Replace category with region in SQL
            corrected_sql = parsed.sql.replace("category", "region").replace("CATEGORY", "region")
            parsed.sql = corrected_sql
            if parsed.viz and parsed.viz.groupBy:
                parsed.viz.groupBy = [g if g != "category" else "region" for g in parsed.viz.groupBy]
            if parsed.viz and parsed.viz.x == "category":
                parsed.viz.x = "region"

    rows = None
    schema = None
    if parsed.sql:
        ok, msg = validate_sql(parsed.sql)
        if not ok:
            return ChatPayload(answer=f"Unsafe SQL: {msg}", sql=parsed.sql, viz=parsed.viz)
        try:
            result_rows = repo.query(parsed.sql)
            rows = result_rows[:5000]
            schema = [ColumnSchema(name=c["name"], type=c["type"]) for c in repo.infer_schema(rows)]
        except Exception as db_error:
            # Database error - include translated SQL in response for debugging
            error_msg = str(db_error)
            # If it's a ClickHouse-specific error, try to provide helpful context
            if "CURRENT_DATE" in parsed.sql.upper() and "Unknown expression" in error_msg:
                return ChatPayload(
                    answer=f"SQL Translation Error: The query still contains CURRENT_DATE after translation. This shouldn't happen. SQL: {parsed.sql[:200]}",
                    sql=parsed.sql,
                    viz=parsed.viz
                )
            return ChatPayload(
                answer=f"Database error: {error_msg[:300]}",
                sql=parsed.sql,
                viz=parsed.viz
            )

    return ChatPayload(answer=parsed.answer, sql=parsed.sql, viz=parsed.viz, rows=rows, schema=schema)

