from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from .config import LLMConfig


@dataclass
class LLMClient:
    client: Any
    model: str

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        client = OpenAI(base_url=config.base_url, api_key=config.api_key)
        return cls(client=client, model=config.model)

    def chat(self, prompt: str, *, max_tokens: int = 250) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()

    def agent_loop(
        self,
        system_prompt: str,
        user_query: str,
        tools: list[dict[str, Any]],
        tool_handlers: dict[str, Any],
        max_iterations: int = 5,
        max_tokens: int = 400,
    ) -> str:
        """
        Runs the ReAct execution loop using native tool calling.
        """
        import json
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        for _ in range(max_iterations):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=max_tokens,
                    stream=True,
                )
            except Exception as e:
                yield f"\n\n⚠️ API Error: {e}"
                return

            tool_calls = []
            full_content = ""

            for chunk in response:
                delta = chunk.choices[0].delta
                
                # 1. Accumulate Tool Calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        # Ensure list is long enough
                        while len(tool_calls) <= tc.index:
                            tool_calls.append({
                                "id": "", 
                                "type": "function", 
                                "function": {"name": "", "arguments": ""}
                            })
                        
                        if tc.id:
                            tool_calls[tc.index]["id"] = tc.id
                        if tc.function.name:
                            tool_calls[tc.index]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

                # 2. Yield text content directly to frontend
                if delta.content:
                    full_content += delta.content
                    yield delta.content

            # If no tools were called, the text we just yielded is the final answer!
            if not tool_calls:
                return

            # Otherwise, the model called tools. We append its action to history.
            assistant_msg = {
                "role": "assistant",
                "content": full_content if full_content else "",
                "tool_calls": tool_calls
            }
            messages.append(assistant_msg)

            # Execute the tools and feed results back to the LLM
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                try:
                    func_args = json.loads(tool_call["function"]["arguments"])
                    if func_name in tool_handlers:
                        tool_result = tool_handlers[func_name](**func_args)
                    else:
                        tool_result = f"Error: Tool {func_name} not found."
                except Exception as e:
                    tool_result = f"Error executing tool: {e}"
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(tool_result)
                })

        yield "\n\n⚠️ Agent stopped: Reached maximum thinking steps."


