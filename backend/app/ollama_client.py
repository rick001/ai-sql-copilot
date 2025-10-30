from typing import Any, Dict, List, Optional
import json
import httpx
from .settings import Settings

class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.ollama_url or "http://localhost:11434"
        self.model = settings.ollama_model or "llama3.1:8b"
        self.client = httpx.AsyncClient(timeout=120.0)

    def load_system_prompt(self) -> str:
        from .bedrock_client import BedrockClient
        # Reuse the same system prompt loader
        temp = BedrockClient(self.settings)
        return temp.load_system_prompt()

    async def converse(self, system_prompt: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_runner) -> Dict[str, Any]:
        # Ollama uses OpenAI-compatible chat format but needs tools formatted differently
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                ollama_messages.append({"role": "user", "content": content})
        
        # Convert tools to OpenAI function calling format for Ollama
        functions = []
        for tool in tools:
            tool_spec = tool.get("toolSpec", tool)
            input_schema = tool_spec.get("inputSchema", {}).get("json", tool_spec.get("inputSchema", {}))
            # Ollama expects OpenAI format: type + function wrapper
            functions.append({
                "type": "function",
                "function": {
                    "name": tool_spec.get("name"),
                    "description": tool_spec.get("description", ""),
                    "parameters": input_schema
                }
            })

        # First call: system prompt + user message
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
            ] + ollama_messages,
            "options": {
                "temperature": 0.2,
            }
        }
        
        if functions:
            payload["tools"] = functions
            payload["tool_choice"] = "auto"

        try:
            # Disable streaming for now
            payload["stream"] = False
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            # Handle both single JSON object and newline-delimited JSON
            response_text = response.text.strip()
            if isinstance(response_text, dict):
                result = response_text
            else:
                try:
                    result = json.loads(response_text)
                except (json.JSONDecodeError, TypeError) as e:
                    # Try parsing first line if multiple JSON objects
                    first_line = response_text.split('\n')[0] if '\n' in response_text else response_text
                    try:
                        result = json.loads(first_line)
                    except (json.JSONDecodeError, TypeError):
                        # Last resort: wrap text in message structure
                        result = {"message": {"content": str(response_text)}}
            
            # Check for tool calls in response
            message = result.get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            if tool_calls:
                # Execute tools - with retry mechanism
                max_retries = 2  # Initial attempt + 1 retry
                attempt = 0
                successful_tool_result = None
                
                while attempt < max_retries:
                    attempt += 1
                    tool_executed = False
                    
                    for call in tool_calls:
                        function_info = call.get("function", {})
                        function_name = function_info.get("name")
                        # Ollama returns arguments as dict, not string
                        function_args = function_info.get("arguments", {})
                        if not isinstance(function_args, dict):
                            # Fallback: try to parse if string
                            try:
                                function_args = json.loads(function_args) if isinstance(function_args, str) else {}
                            except (json.JSONDecodeError, TypeError):
                                function_args = {}
                        
                        tool_result = tool_runner.run(function_name, function_args)
                        tool_executed = True
                        
                        # If tool execution failed, try to get Ollama to retry
                        if "error" in tool_result:
                            if attempt < max_retries:
                                # Add error feedback
                                error_msg = tool_result.get("error", "Unknown error")
                                hint = tool_result.get("hint", "")
                                
                                feedback = f"SQL execution failed: {error_msg}"
                                if hint:
                                    feedback += f"\nHint: {hint}"
                                feedback += "\n\nPlease generate a corrected, complete SQL query. The query must include: SELECT columns FROM retail_sales [WHERE/GROUP BY/ORDER BY clauses]."
                                
                                ollama_messages.append({
                                    "role": "tool",
                                    "content": json.dumps(tool_result),
                                    "name": function_name
                                })
                                
                                ollama_messages.append({
                                    "role": "user",
                                    "content": feedback
                                })
                                
                                # Retry call with error feedback
                                payload_retry = {
                                    "model": self.model,
                                    "messages": [
                                        {"role": "system", "content": system_prompt},
                                    ] + ollama_messages,
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.1,  # Lower temperature for more precise SQL
                                    }
                                }
                                
                                if functions:
                                    payload_retry["tools"] = functions
                                    payload_retry["tool_choice"] = "auto"
                                
                                response_retry = await self.client.post(
                                    f"{self.base_url}/api/chat",
                                    json=payload_retry
                                )
                                response_retry.raise_for_status()
                                response_retry_text = response_retry.text.strip()
                                
                                try:
                                    result_retry = json.loads(response_retry_text)
                                except json.JSONDecodeError:
                                    first_line = response_retry_text.split('\n')[0] if '\n' in response_retry_text else response_retry_text
                                    try:
                                        result_retry = json.loads(first_line)
                                    except json.JSONDecodeError:
                                        result_retry = {"message": {"content": response_retry_text}}
                                
                                message_retry = result_retry.get("message", {})
                                tool_calls_retry = message_retry.get("tool_calls", [])
                                
                                # If retry generated a new tool call, update tool_calls for next iteration
                                if tool_calls_retry:
                                    tool_calls = tool_calls_retry
                                    break  # Break inner loop, continue while loop
                                else:
                                    # No tool call generated, break retry loop
                                    attempt = max_retries
                                    break
                            else:
                                # Max retries reached, use error result
                                successful_tool_result = tool_result
                                ollama_messages.append({
                                    "role": "tool",
                                    "content": json.dumps(tool_result),
                                    "name": function_name
                                })
                                break
                        else:
                            # Success!
                            successful_tool_result = tool_result
                            ollama_messages.append({
                                "role": "tool",
                                "content": json.dumps(tool_result),
                                "name": function_name
                            })
                            attempt = max_retries  # Exit retry loop
                            break
                    
                    # If tool was executed and succeeded, break retry loop
                    if tool_executed and successful_tool_result and "error" not in successful_tool_result:
                        break
                
                # Final call with tool results (only proceed if we have successful results)
                if successful_tool_result and "error" not in successful_tool_result:
                    payload_final = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                        ] + ollama_messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                        }
                    }
                    response_final = await self.client.post(
                        f"{self.base_url}/api/chat",
                        json=payload_final
                    )
                    response_final.raise_for_status()
                    response_final_text = response_final.text.strip()
                    try:
                        result_final = json.loads(response_final_text)
                    except json.JSONDecodeError:
                        first_line = response_final_text.split('\n')[0] if '\n' in response_final_text else response_final_text
                        try:
                            result_final = json.loads(first_line)
                        except json.JSONDecodeError:
                            result_final = {"message": {"content": response_final_text}}
                    message = result_final.get("message", {})
                else:
                    # If we have errors, construct a response from the error
                    message = {
                        "content": f"I encountered an error executing the SQL query: {json.loads(ollama_messages[-1].get('content', '{}')).get('error', 'Unknown error')}"
                    }
            
            # Extract answer from message
            answer_text = message.get("content", "")
            
            # Handle case where content might already be a dict
            if isinstance(answer_text, dict):
                if "answer" in answer_text:
                    return answer_text
                answer_text = str(answer_text)
            
            # Ensure answer_text is a string
            if not isinstance(answer_text, str):
                answer_text = str(answer_text)
            
            # Ollama may return JSON as an escaped string, so try parsing twice
            try:
                # First parse: might get a string
                parsed = json.loads(answer_text)
                if isinstance(parsed, str):
                    # It's a JSON-encoded string, parse again
                    parsed = json.loads(parsed)
                # Validate it has at least 'answer' key
                if isinstance(parsed, dict) and "answer" in parsed:
                    # Clean up empty strings in viz spec before returning
                    parsed = self._clean_viz_spec(parsed)
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Fallback: try to extract JSON from text (might be embedded in markdown or text)
            start = answer_text.find("{")
            end = answer_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    candidate = answer_text[start:end+1]
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "answer" in parsed:
                        # Clean up empty strings in viz spec
                        parsed = self._clean_viz_spec(parsed)
                        return parsed
                except json.JSONDecodeError:
                    pass
            
            # If no JSON found, try to extract SQL from text (simple heuristic)
            sql = None
            if "SELECT" in answer_text.upper() or "FROM retail_sales" in answer_text.lower():
                # Try to extract SQL statement
                sql_match = None
                for line in answer_text.split('\n'):
                    if 'SELECT' in line.upper():
                        # Find SQL block
                        sql_start = answer_text.upper().find('SELECT')
                        if sql_start != -1:
                            # Find end (semicolon or newline)
                            sql_end = answer_text.find(';', sql_start)
                            if sql_end == -1:
                                sql_end = len(answer_text)
                            sql = answer_text[sql_start:sql_end].strip()
                            break
            
            # Return minimal envelope with extracted SQL if found
            result = {"answer": answer_text}  # Remove truncation to see full response
            if sql:
                result["sql"] = sql
            # Clean up any viz spec before returning
            result = self._clean_viz_spec(result)
            return result
        finally:
            await self.client.aclose()
    
    def _clean_viz_spec(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up empty strings in viz spec to convert them to None"""
        if isinstance(data, dict) and "viz" in data and isinstance(data["viz"], dict):
            viz = data["viz"]
            # Convert empty strings to None for optional fields
            if "x" in viz and viz["x"] == "":
                viz["x"] = None
            if "y" in viz:
                if isinstance(viz["y"], list) and len(viz["y"]) == 0:
                    viz["y"] = None
                elif isinstance(viz["y"], list):
                    # Remove empty strings from y list
                    viz["y"] = [v for v in viz["y"] if v != ""]
                    if len(viz["y"]) == 0:
                        viz["y"] = None
            if "groupBy" in viz:
                if isinstance(viz["groupBy"], list) and len(viz["groupBy"]) == 0:
                    viz["groupBy"] = None
                elif isinstance(viz["groupBy"], list):
                    # Remove empty strings from groupBy list
                    viz["groupBy"] = [v for v in viz["groupBy"] if v != ""]
                    if len(viz["groupBy"]) == 0:
                        viz["groupBy"] = None
        return data

