from typing import Any, Dict, List, Optional
import json
import os
import re
import boto3
from botocore.config import Config
from .settings import Settings

class BedrockClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._mock = settings.bedrock_mock == 1
        if not self._mock:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=settings.aws_region,
                config=Config(retries={"max_attempts": 3})
            )
        else:
            self.client = None

    def load_system_prompt(self) -> str:
        path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "You are an analytics assistant. Use the query_sql tool to answer."

    async def converse(self, system_prompt: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_runner) -> Dict[str, Any]:
        if self._mock:
            user_text = " ".join([m.get("content", "") for m in messages if m.get("role") == "user"]).lower()
            # Heuristic intent routing for demo
            is_top = "top" in user_text or "best" in user_text
            mentions_product = ("product" in user_text) or ("sku" in user_text)
            mentions_units = "unit" in user_text
            mentions_sales = ("sales" in user_text) or ("revenue" in user_text)
            mentions_quarter = "quarter" in user_text
            mentions_compare = "compare" in user_text or "vs" in user_text
            mentions_price = "price" in user_text or "avg price" in user_text or "average price" in user_text

            if is_top and mentions_product and mentions_sales:
                # Top products by net sales, optionally scoped to roughly last quarter (90 days)
                where_clause = "WHERE date >= current_date - INTERVAL 90 DAY" if mentions_quarter else ""
                sql = f"SELECT sku, SUM(net_sales) AS net_sales FROM retail_sales {where_clause} GROUP BY sku ORDER BY net_sales DESC LIMIT 10"
                result = tool_runner.run("query_sql", {"sql": sql})
                return {
                    "answer": "Top products by net sales" + (" in the last quarter" if mentions_quarter else "") + ".",
                    "sql": sql,
                    "viz": {
                        "type": "bar",
                        "x": "category",
                        "y": ["net_sales"],
                        "groupBy": ["sku"],
                        "aggregation": "sum",
                        "explanations": ["Sorted by total net sales", "Limit 10"]
                    }
                }

            if is_top and mentions_product and mentions_units:
                sql = "SELECT sku, SUM(units) AS units FROM retail_sales GROUP BY sku ORDER BY units DESC LIMIT 10"
                result = tool_runner.run("query_sql", {"sql": sql})
                return {
                    "answer": "Top products by units sold.",
                    "sql": sql,
                    "viz": {
                        "type": "bar",
                        "x": "category",
                        "y": ["units"],
                        "groupBy": ["sku"],
                        "aggregation": "sum",
                        "explanations": ["Sorted by total units", "Limit 10"]
                    }
                }

            if mentions_compare and mentions_price and mentions_product:
                # Approximate comparison via avg unit price for top 10 by units
                sql = (
                    "SELECT sku, SUM(units) AS units, "
                    "CASE WHEN SUM(units)=0 THEN NULL ELSE SUM(net_sales)/SUM(units) END AS avg_unit_price "
                    "FROM retail_sales GROUP BY sku ORDER BY units DESC LIMIT 10"
                )
                result = tool_runner.run("query_sql", {"sql": sql})
                return {
                    "answer": "Average unit price for top-selling SKUs (approximation).",
                    "sql": sql,
                    "viz": {
                        "type": "bar",
                        "x": "category",
                        "y": ["avg_unit_price"],
                        "groupBy": ["sku"],
                        "aggregation": "avg",
                        "explanations": ["avg_unit_price = net_sales / units"]
                    }
                }

            # Default demo: sales over time by region
            sql = "SELECT date, region, sum(net_sales) AS net_sales FROM retail_sales GROUP BY date, region ORDER BY date"
            result = tool_runner.run("query_sql", {"sql": sql})
            return {
                "answer": "Here is a breakdown of net sales over time by region.",
                "sql": sql,
                "viz": {
                    "type": "line",
                    "x": "date",
                    "y": ["net_sales"],
                    "groupBy": ["region"],
                    "aggregation": "sum",
                    "explanations": ["Summed by date and region"]
                }
            }

        # Real Bedrock Converse API interaction with tool use handling
        tool_map = {t["toolSpec"]["name"]: t for t in tools}

        # First call: system prompt + user message
        system = [{"text": system_prompt}]
        conversation_messages = messages

        response = self._invoke_converse(system, conversation_messages, tools)
        tool_calls = self._extract_tool_calls(response)
        if not tool_calls:
            return self._extract_json_envelope(response)

        # Extract the assistant's response content (which includes toolUse blocks)
        # This is required - Bedrock needs to see the toolUse blocks before toolResult blocks
        output = response.get("output", {})
        assistant_message = output.get("message", {})
        assistant_content = assistant_message.get("content", [])
        
        # Add the assistant's response to conversation history (includes toolUse blocks)
        conversation_messages.append({
            "role": "assistant",
            "content": assistant_content
        })

        # Execute tools and collect tool results
        tool_results = []
        for call in tool_calls:
            name = call.get("name")
            input_json = call.get("input") or {}
            result = tool_runner.run(name, input_json)
            tool_use_id = call.get("toolUseId") or call.get("id", "")
            # Bedrock Converse API format: toolUseId must be inside toolResult
            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "status": "success",
                    "content": [{"text": json.dumps(result)}]
                }
            })

        # Add all tool results in a single user message
        # Bedrock expects all toolResults to match the toolUses from the previous assistant message
        if tool_results:
            conversation_messages.append({
                "role": "user",
                "content": tool_results
            })

        # Final call with tool results
        response2 = self._invoke_converse(system, conversation_messages, tools)
        return self._extract_json_envelope(response2)

    def _invoke_converse(self, system: List[Dict[str, str]], messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Try Converse API first, fallback to Chat API if not available
        try:
            # Convert messages to Converse API format
            formatted_messages = []
            for msg in messages:
                role = msg.get("role")
                if role == "user":
                    content = msg.get("content")
                    if isinstance(content, str):
                        formatted_messages.append({"role": "user", "content": [{"text": content}]})
                    elif isinstance(content, list):
                        formatted_messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    content = msg.get("content")
                    if isinstance(content, str):
                        formatted_messages.append({"role": "assistant", "content": [{"text": content}]})
                    elif isinstance(content, list):
                        formatted_messages.append({"role": "assistant", "content": content})
            
            # Call Converse API
            response = self.client.converse(
                modelId=self.settings.bedrock_model_id,
                system=system,
                messages=formatted_messages,
                toolConfig={"tools": tools} if tools else None,
                inferenceConfig={
                    "maxTokens": 2048,  # Increased for better responses
                    "temperature": 0.2,
                }
            )
            return response
        except Exception as e:
            error_str = str(e)
            # Only fallback to Chat API for specific cases, not for invalid model ID
            # If model ID is invalid in Converse, it will also be invalid in Chat API
            if "model identifier is invalid" in error_str.lower() or "invalid model" in error_str.lower():
                # Don't fallback - raise the error so user knows the model ID is wrong
                raise
            # For other ValidationExceptions or Converse errors, try Chat API
            if "ValidationException" in error_str:
                # Log that we're falling back, but some models don't support Chat API
                # So we might still fail, but at least we tried
                try:
                    return self._invoke_chat_api(system, messages, tools)
                except Exception as chat_error:
                    # If Chat API also fails, raise the original Converse error
                    # This gives better error message about the actual issue
                    raise e from chat_error
            raise

    def _invoke_chat_api(self, system: List[Dict[str, str]], messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Fallback to Chat API (invoke_model) format
        # Build messages in Chat API format
        chat_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(content, str):
                chat_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle Chat API format: content can be tool results
                chat_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("text"):
                            chat_content.append(item.get("text"))
                        elif item.get("toolResult"):
                            # Tool result in Chat API format: type="tool_result"
                            tool_result = item["toolResult"]
                            tool_use_id = item.get("toolUseId")
                            result_text = tool_result.get("content", [{}])[0].get("text", "{}")
                            chat_content.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result_text
                            })
                if len(chat_content) == 1 and isinstance(chat_content[0], str):
                    chat_messages.append({"role": role, "content": chat_content[0]})
                else:
                    chat_messages.append({"role": role, "content": chat_content})
        
        # System prompt as first message
        system_text = system[0].get("text", "") if system else ""
        
        # Convert tools from Converse format to Chat API format
        chat_tools = []
        if tools:
            for tool in tools:
                tool_spec = tool.get("toolSpec", tool)
                input_schema_raw = tool_spec.get("inputSchema", {})
                # Extract the actual JSON schema from nested structure
                input_schema = input_schema_raw.get("json", input_schema_raw)
                chat_tools.append({
                    "name": tool_spec.get("name"),
                    "description": tool_spec.get("description", ""),
                    "input_schema": input_schema
                })
        
        # Chat API body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.2,
            "system": system_text,
            "messages": chat_messages,
        }
        
        if chat_tools:
            body["tools"] = chat_tools
        
        # Try the configured model ID, then try common variants
        model_ids_to_try = [
            self.settings.bedrock_model_id,
            "anthropic.claude-3-5-sonnet-20240620-v1:0",  # Commonly available version
            "anthropic.claude-3-5-sonnet-20241022:0",
            "anthropic.claude-3-5-sonnet-v2:0",
            "anthropic.claude-3-5-sonnet-v1:0",
        ]
        
        response = None
        last_error = None
        for model_id in model_ids_to_try:
            try:
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                )
                break
            except Exception as e:
                last_error = e
                if model_id == model_ids_to_try[-1]:
                    raise last_error
                continue
        
        if response is None:
            raise last_error or Exception("Failed to invoke model")
        
        response_body = json.loads(response["body"].read())
        # Convert Chat API response to Converse-like format
        # Chat API returns content as array of blocks (text or tool_use)
        content_blocks = response_body.get("content", [])
        formatted_content = []
        for block in content_blocks:
            if block.get("type") == "text":
                formatted_content.append({"text": block.get("text", "")})
            elif block.get("type") == "tool_use":
                formatted_content.append({"toolUse": {
                    "toolUseId": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {})
                }})
        return {"output": {"message": {"content": formatted_content}}}

    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Try Converse API format first
        tool_uses = []
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        for item in content:
            if item.get("toolUse"):
                tool_uses.append(item["toolUse"])
        # If no tool uses in Converse format, try Chat API format
        if not tool_uses and isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_uses.append({
                        "toolUseId": item.get("id"),
                        "name": item.get("name"),
                        "input": item.get("input", {})
                    })
        return tool_uses

    def _extract_json_envelope(self, response: Dict[str, Any]) -> Dict[str, Any]:
        # Converse API returns text in output.message.content[].text
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        text_parts = [item.get("text", "") for item in content if item.get("text")]
        text = " ".join(text_parts)
        
        if isinstance(text, dict):
            return text
        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                candidate = text[start:end+1]
                try:
                    return json.loads(candidate)
                except Exception:
                    pass
        return {"answer": text[:200]}

