from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, field_validator
import time
import html
 
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)  # отключаем публичные доки
 
# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # только dev-фронт
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
 
# ── Rate limiting (простой in-memory) ─────────────────────────────────────────
RATE_LIMIT = 20          # запросов
RATE_WINDOW = 60         # в секунду
_rate_store: dict[str, list[float]] = {}
 
def check_rate_limit(ip: str) -> None:
    now = time.time()
    hits = _rate_store.get(ip, [])
    hits = [t for t in hits if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Слишком много запросов. Подождите немного.")
    hits.append(now)
    _rate_store[ip] = hits
 
# ── Модели ────────────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str
 
    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v
 
    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content cannot be empty")
        if len(v) > 8000:
            raise ValueError("content too long (max 8000 chars)")
        return html.escape(v)          # экранируем HTML-символы
 
 
class ChatRequest(BaseModel):
    messages: list[Message]
 
    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("messages list cannot be empty")
        if len(v) > 100:
            raise ValueError("too many messages in history (max 100)")
        return v
 
 
class ChatResponse(BaseModel):
    reply: str
 
 
# ── Заглушка нейросети — замените эту функцию ─────────────────────────────────
def call_neural_network(messages: list[dict]) -> str:
    """
    TODO: вставьте сюда вызов вашей нейронной сети.
 
    `messages` — список словарей вида:
        [
            {"role": "user",      "content": "Привет!"},
            {"role": "assistant", "content": "Привет! Чем могу помочь?"},
            {"role": "user",      "content": "Расскажи анекдот."},
        ]
 
    Верните строку с ответом ассистента.
 
    Пример для OpenAI:
        from openai import OpenAI
        client = OpenAI(api_key="...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return response.choices[0].message.content
 
    Пример для Anthropic:
        import anthropic
        client = anthropic.Anthropic(api_key="...")
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=messages,
        )
        return response.content[0].text
    """
    from system_prompt import system_prompt
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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",
    )

    messages = [{'role': 'system', 'content': [{'type': 'text', 'text': system_prompt}]}, *messages]
    completion = client.chat.completions.create(
        model="google/gemini-2.5-flash-lite",
        messages=messages
    )
    answer = completion.choices[0].message.content
    print(f"ANSWER: {answer}")

    return answer
 
 
# ── Endpoint ──────────────────────────────────────────────────────────────────
from fastapi import Request
 
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    # rate limit по IP
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)
 
    messages_dicts = [{"role": m.role, "content": m.content} for m in body.messages]
 
    try:
        reply = call_neural_network(messages_dicts)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка нейросети: {str(e)}")
 
    if not reply or not reply.strip():
        raise HTTPException(status_code=502, detail="Нейросеть вернула пустой ответ.")
 
    return ChatResponse(reply=reply.strip())
