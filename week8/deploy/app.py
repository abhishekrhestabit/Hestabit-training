import uuid, time, logging, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from model_loader import get_model, format_prompt, format_chat
from config import MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_TOP_K, HOST, PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload model on startup."""
    get_model()
    yield

app = FastAPI(title="TinyLlama Inference API", version="1.0.0", lifespan=lifespan)


# ─── Request / Response schemas ───

class GenerateRequest(BaseModel):
    prompt: str
    input_text: str = ""
    system: str = ""
    max_tokens: int = Field(default=MAX_TOKENS, ge=1, le=2048)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULT_TOP_P, ge=0.0, le=1.0)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=0)
    stream: bool = False

class ChatMessage(BaseModel):
    role: str = "user"  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    reset_history: bool = False
    system: str = "You are a helpful assistant."
    max_tokens: int = Field(default=MAX_TOKENS, ge=1, le=2048)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULT_TOP_P, ge=0.0, le=1.0)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=0)
    stream: bool = False

class GenerateResponse(BaseModel):
    request_id: str
    text: str
    tokens: int
    time_s: float

class ChatResponse(BaseModel):
    request_id: str
    session_id: str | None = None
    role: str = "assistant"
    content: str
    tokens: int
    time_s: float


# ─── Helpers ───

STOP_SEQS = ["### Instruction:", "### System:", "### Input:", "\nYou:", "\nUser:"]
MAX_HISTORY_TURNS = 10  # keep last 10 user+assistant pairs (20 messages)
chat_histories: dict[str, list[dict[str, str]]] = {}


def _trim_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Trim chat history to the same turn limit used by CLI mode."""
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        return history[-max_messages:]
    return history

def _generate(prompt: str, max_tokens: int, temperature: float, top_p: float, top_k: int):
    """Run non-streaming generation."""
    model = get_model()
    t0 = time.perf_counter()
    out = model(prompt, max_tokens=max_tokens, temperature=temperature, top_p=top_p, top_k=top_k, echo=False, stream=False, stop=STOP_SEQS)
    elapsed = time.perf_counter() - t0
    text = out["choices"][0]["text"].strip()  # type: ignore[index]
    tokens = out.get("usage", {}).get("completion_tokens", 0)  # type: ignore[union-attr]
    return text, tokens, elapsed


def _stream(prompt: str, max_tokens: int, temperature: float, top_p: float, top_k: int, session_id: str | None = None):
    """Yield SSE chunks for streaming generation."""
    model = get_model()
    collected: list[str] = []
    for chunk in model(prompt, max_tokens=max_tokens, temperature=temperature, top_p=top_p, top_k=top_k, echo=False, stream=True, stop=STOP_SEQS):
        token = chunk["choices"][0]["text"]  # type: ignore[index]
        collected.append(token)
        yield f"data: {json.dumps({'token': token})}\n\n"

    if session_id:
        history = chat_histories.get(session_id, [])
        history.append({"role": "assistant", "content": "".join(collected).strip()})
        chat_histories[session_id] = _trim_history(history)

    yield "data: [DONE]\n\n"


# ─── Endpoints ───

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """Single-prompt generation with optional streaming."""
    rid = str(uuid.uuid4())[:8]
    prompt = format_prompt(req.prompt, req.input_text, req.system)
    logger.info(f"[{rid}] /generate prompt_len={len(prompt)} stream={req.stream}")

    if req.stream:
        return StreamingResponse(_stream(prompt, req.max_tokens, req.temperature, req.top_p, req.top_k),
                                 media_type="text/event-stream")
    text, tokens, elapsed = _generate(prompt, req.max_tokens, req.temperature, req.top_p, req.top_k)
    logger.info(f"[{rid}] completed tokens={tokens} time={elapsed:.2f}s")
    return GenerateResponse(request_id=rid, text=text, tokens=tokens, time_s=round(elapsed, 3))


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Multi-turn chat with optional server-side history by session_id."""
    rid = str(uuid.uuid4())[:8]
    incoming = [{"role": m.role, "content": m.content} for m in req.messages]

    if req.session_id:
        if req.reset_history or req.session_id not in chat_histories:
            chat_histories[req.session_id] = []
        history = chat_histories[req.session_id]

        if incoming:
            # A single user message follows the same incremental pattern as CLI chat.
            if len(incoming) == 1 and incoming[0].get("role") == "user":
                history.append(incoming[0])
            else:
                # If client sends full history, replace and trim server-side copy.
                history = incoming
            chat_histories[req.session_id] = _trim_history(history)

        messages = chat_histories[req.session_id]
    else:
        if not incoming:
            raise HTTPException(status_code=400, detail="Provide at least one message or use session_id with history.")
        messages = _trim_history(incoming)

    prompt = format_chat(messages, req.system)
    logger.info(
        f"[{rid}] /chat turns={len(messages)} prompt_len={len(prompt)} stream={req.stream} session_id={req.session_id}"
    )

    if req.stream:
        return StreamingResponse(_stream(prompt, req.max_tokens, req.temperature, req.top_p, req.top_k, req.session_id),
                                 media_type="text/event-stream")
    text, tokens, elapsed = _generate(prompt, req.max_tokens, req.temperature, req.top_p, req.top_k)

    if req.session_id:
        history = chat_histories.get(req.session_id, [])
        history.append({"role": "assistant", "content": text})
        chat_histories[req.session_id] = _trim_history(history)

    logger.info(f"[{rid}] completed tokens={tokens} time={elapsed:.2f}s")
    return ChatResponse(request_id=rid, session_id=req.session_id, content=text, tokens=tokens, time_s=round(elapsed, 3))


@app.get("/")
async def root():
    return {"service": "TinyLlama Inference API", "endpoints": ["POST /generate", "POST /chat", "GET /health", "GET /docs"]}

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": get_model() is not None}


# ─── CLI mode ───

def cli_chat():
    """Interactive terminal chat mode."""
    print("TinyLlama Chat (type 'quit' to exit)\n")
    model = get_model()
    history, system = [], "You are a helpful assistant."

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        history.append({"role": "user", "content": user_input})

        history = _trim_history(history)

        prompt = format_chat(history, system)

        print("Bot: ", end="", flush=True)
        full_response = []
        for chunk in model(prompt, max_tokens=MAX_TOKENS, temperature=0.7, top_p=0.9, top_k=40, echo=False, stream=True, stop=STOP_SEQS):
            token = chunk["choices"][0]["text"]  # type: ignore[index]
            print(token, end="", flush=True)
            full_response.append(token)
        print()
        history.append({"role": "assistant", "content": "".join(full_response).strip()})
        history = _trim_history(history)


if __name__ == "__main__":
    import sys
    if "--cli" in sys.argv:
        cli_chat()
    else:
        import uvicorn
        uvicorn.run(app, host=HOST, port=PORT)
