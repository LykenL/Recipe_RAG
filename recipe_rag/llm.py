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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=max_tokens,
            )
            
            message = response.choices[0].message
            
            # If the model does not want to call any tools, it's done.
            if not getattr(message, "tool_calls", None):
                return message.content.strip()

            # The model called tools. Append the assistant's action to history.
            messages.append(message.model_dump(exclude_unset=True))

            # Execute each tool
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                # Execute the bound python function
                if func_name in tool_handlers:
                    try:
                        tool_result = tool_handlers[func_name](**func_args)
                    except Exception as e:
                        tool_result = f"Error executing tool: {e}"
                else:
                    tool_result = f"Error: Tool {func_name} not found."
                
                # Append tool result to history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result)
                })

        # Fallback if max_iterations exceeded
        return "Agent stopped: Reached maximum thinking steps."


