---
name: freellmapi-integration
description: >-
  Guides setup and integration of FreeLLMAPI (github.com/tashfeenahmed/freellmapi)
  as a unified OpenAI-compatible or Anthropic-compatible LLM gateway. Use when
  configuring FreeLLMAPI endpoints, routing strategies (auto, auto:fast, auto:smart),
  Python/Node.js OpenAI SDK clients, or coding-agent connections across projects.
---

# FreeLLMAPI Integration

FreeLLMAPI aggregates free LLM provider tiers and custom OpenAI-compatible endpoints behind a single `/v1` API with automatic failover, rate-limit cooldowns, and per-key usage tracking.

## 1. Base URLs & Authentication

- **Server / Docker install**: `http://localhost:3001/v1` (or bare `http://localhost:3001` for Anthropic Messages clients)
- **Desktop app**: `http://127.0.0.1:31415/v1` (or bare `http://127.0.0.1:31415` for Anthropic Messages clients)
- **API Key**: Use the unified key generated on the FreeLLMAPI dashboard's **Keys** page.
- **OpenAPI Docs**: `GET /v1/docs` (interactive) and `GET /v1/openapi.json`

Never hardcode your unified key in source files — load it from `FREELLMAPI_API_KEY` or `OPENAI_API_KEY` in `.env` (and keep `.env` gitignored).

## 2. Python Integration (OpenAI SDK)

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:3001/v1"),
    api_key=os.environ["OPENAI_API_KEY"],
)

resp = client.chat.completions.create(
    model="auto",  # or "auto:fast", "auto:smart", "auto:reliable", "auto:<profile>"
    messages=[{"role": "user", "content": "Hello"}],
)
print(resp.choices[0].message.content)
```

## 3. Node.js / TypeScript Integration

```typescript
const baseUrl = process.env.OPENAI_BASE_URL ?? "http://localhost:3001/v1";
const apiKey = process.env.OPENAI_API_KEY!;

const res = await fetch(`${baseUrl}/chat/completions`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "auto:fast",
    messages: [{ role: "user", content: "Hello" }],
  }),
});
const data = await res.json();
```

## 4. Routing Strategies (`auto:*`)

- `auto` — Follows your active fallback chain.
- `auto:smart` — Favors highest-intelligence models.
- `auto:fast` — Favors measured throughput and time-to-first-byte.
- `auto:reliable` — Favors recent success rate.
- `auto:balanced` — Default blend of reliability, speed, and intelligence.
- `auto:<profile-name>` — Routes through a named fallback chain profile (returns `400` if unknown).

## 5. Model Discovery & Health Check

Query ready-to-serve models before dispatching:

```bash
curl "http://localhost:3001/v1/models?execution_status=ready" \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

`execution_status` values: `ready`, `needsKey`, `exhausted`.
