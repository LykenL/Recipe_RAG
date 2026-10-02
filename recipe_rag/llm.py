from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

from openai import OpenAI

from .config import LLMConfig

#: Substrings that indicate the endpoint rejected `tools`, not a real failure.
_TOOL_UNSUPPORTED_MARKERS = (
    "tool",
    "function",
    "not supported",
    "unsupported",
    "does not support",
)


@dataclass
class LLMClient:
    client: Any
    model: str
    temperature: float = 0.2
    request_timeout: float = 120.0
    #: set False after the endpoint rejects `tools`, so we stop retrying
    supports_tools: bool = field(default=True, repr=False)

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=cls.request_timeout,
            max_retries=2,
        )
        return cls(client=client, model=config.model)

    def chat(self, prompt: str, *, max_tokens: int = 250) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=self.temperature,
        )
        return resp.choices[0].message.content.strip()

    # ── agent loop ───────────────────────────────────────────────────────────
    def _build_messages(
        self,
        system_prompt: str,
        user_query: str,
        history: Sequence[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for turn in history or []:
            role = (turn or {}).get("role")
            content = (turn or {}).get("content")
            # Only plain user/assistant text is replayed; tool turns from earlier
            # requests are deliberately dropped so history stays portable.
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_query})
        return messages

    def agent_loop(
        self,
        system_prompt: str,
        user_query: str,
        tools: list[dict[str, Any]],
        tool_handlers: dict[str, Any],
        history: Sequence[dict[str, Any]] | None = None,
        max_iterations: int = 5,
        max_tokens: int = 400,
    ) -> Iterator[str]:
        """ReAct-style loop over native tool calling. Yields assistant text as it streams."""
        import json

        messages = self._build_messages(system_prompt, user_query, history)

        for _ in range(max_iterations):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": self.temperature,
                "stream": True,
            }
            use_tools = bool(tools) and self.supports_tools
            if use_tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            try:
                response = self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                # Some OpenAI-compatible endpoints reject `tools` outright.
                # Degrade to a plain completion instead of failing the request.
                lowered = str(exc).lower()
                if use_tools and any(m in lowered for m in _TOOL_UNSUPPORTED_MARKERS):
                    self.supports_tools = False
                    kwargs.pop("tools", None)
                    kwargs.pop("tool_choice", None)
                    try:
                        response = self.client.chat.completions.create(**kwargs)
                    except Exception as retry_exc:
                        yield f"\n\n⚠️ API Error: {retry_exc}"
                        return
                else:
                    yield f"\n\n⚠️ API Error: {exc}"
                    return

            tool_calls: list[dict[str, Any]] = []
            full_content = ""

            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if getattr(delta, "tool_calls", None):
                    for tc in delta.tool_calls:
                        while len(tool_calls) <= tc.index:
                            tool_calls.append(
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        if tc.id:
                            tool_calls[tc.index]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls[tc.index]["function"]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

                if delta.content:
                    full_content += delta.content
                    yield delta.content

            # No tools requested -> the text we just streamed is the final answer.
            if not tool_calls:
                return

            messages.append(
                {
                    "role": "assistant",
                    "content": full_content or "",
                    "tool_calls": tool_calls,
                }
            )

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                try:
                    func_args = json.loads(tool_call["function"]["arguments"] or "{}")
                    if func_name in tool_handlers:
                        tool_result = tool_handlers[func_name](**func_args)
                    else:
                        tool_result = f"Error: Tool {func_name} not found."
                except Exception as exc:
                    tool_result = f"Error executing tool: {exc}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(tool_result),
                    }
                )

        yield "\n\n⚠️ Agent stopped: Reached maximum thinking steps."
