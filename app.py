from flask import Flask, jsonify, render_template, request, Response, stream_with_context
import base64
import json
from g4f.client import Client, ClientFactory
from g4f.errors import RateLimitError

app = Flask(__name__)

DEFAULT_MODEL_KEY = "auto"

MODEL_PRESETS = {
    "auto": {
        "name": "AUTO",
        "mode": "client",
        "model": "auto",
    },
    "gemini": {
        "name": "Gemini 2.5 Flash",
        "mode": "client",
        "model": "gemini-2.5-flash",
    },
    "gpt4o": {
        "name": "GPT-4o",
        "mode": "rails",
        "rails": [
            ("pollinations", "openai"),
            ("pollinations", "openai-fast"),
            ("puter", "openai:openai/gpt-4o"),
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "mode": "rails",
        "rails": [
            ("pollinations", "deepseek"),
        ],
    },
    "claude": {
        "name": "Claude",
        "mode": "rails",
        "rails": [
            ("pollinations", "claude-fast"),
            ("AnyProvider", "claude-sonnet-4-5"),
        ],
    },
}

def clean_response(text: str) -> str:
    if not text:
        return ""
    bad_parts = [
        "Need proxies cheaper than the market?",
        "https://op.wtf",
        "```lua",
        "```",
        "lua",
        "model does not exist",
    ]
    for part in bad_parts:
        text = text.replace(part, "")
    return text.strip()

def build_messages(history, message, image_b64=None):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "Answer clearly, to the point. "
                "If an image is sent, describe it in detail. "
                "You must remember the entire conversation history and answer questions by referencing previous messages. "
		"IMPORTANT: When providing code in your responses, ALWAYS wrap it in markdown code blocks with the language specified, like this: ```python your code here ``` or ```javascript your code here ``` etc. Never output code without proper markdown code block formatting with language identifier. "
                "The supported languages you should use for code blocks are: "
                "python, javascript, typescript, java, cpp, csharp, go, rust, sql, bash, json, xml, css, lua. "
                "For example: ```python print('hello')``` or ```javascript console.log('hello')``` or ```bash ls -la``` etc. "
                "Always specify the correct language for syntax highlighting."
            ),
        }
    ]

    # Add entire message history
    for item in history:
        role = item.get("role")
        content = item.get("content", "").strip()
        
        if role in {"user", "assistant"} and content:
            # Check if there is an image in history
            if item.get("image_b64"):
                msg_content = [
                    {"type": "text", "text": content},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{item['image_b64']}"}},
                ]
            else:
                msg_content = content
            
            messages.append({"role": role, "content": msg_content})

    # Add current user message
    if image_b64:
        user_content = [
            {"type": "text", "text": message},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
    else:
        user_content = message
    
    messages.append({"role": "user", "content": user_content})
    
    return messages

def ask_g4f_stream(messages, preset_key):
    preset = MODEL_PRESETS.get(preset_key, MODEL_PRESETS[DEFAULT_MODEL_KEY])

    if preset["mode"] == "rails":
        for provider_name, model_name in preset["rails"]:
            try:
                client = ClientFactory.create_client(provider_name)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                    timeout=60,
                )
                yield provider_name, model_name, response
                return
            except (RateLimitError, Exception):
                continue
        raise RuntimeError(f"All providers for {preset['name']} are unavailable.")

    try:
        client = Client()
        response = client.chat.completions.create(
            model=preset["model"],
            messages=messages,
            stream=True,
        )
        yield "auto", preset["model"], response
    except Exception as exc:
        raise RuntimeError(f"g4f error: {exc}")

def generate_stream(preset_key, messages):
    try:
        for provider, model, stream in ask_g4f_stream(messages, preset_key):
            full_reply = ""
            meta = {"preset": preset_key, "provider": provider, "model": model}
            yield json.dumps({"type": "meta", "meta": meta}) + '\n'

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    full_reply += delta
                    yield json.dumps({"type": "content", "delta": delta}) + '\n'

            yield json.dumps({"type": "end", "content": full_reply}) + '\n'
    except Exception as e:
        yield json.dumps({"type": "error", "error": str(e)}) + '\n'

@app.route("/")
def index():
    return render_template(
        "index.html",
        model_name=MODEL_PRESETS[DEFAULT_MODEL_KEY]["name"],
        model_presets=MODEL_PRESETS,
        default_model_key=DEFAULT_MODEL_KEY,
    )

@app.route("/api/chat", methods=["POST"])  # Keep old non-stream for compatibility
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    preset_key = (data.get("model") or DEFAULT_MODEL_KEY).strip().lower()

    if not message:
        return jsonify({"error": "Empty message"}), 400

    messages = build_messages(history, message)
    try:
        reply, meta = ask_g4f(messages, preset_key)  # Use old non-stream logic
        return jsonify({"reply": reply, "meta": meta})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    preset_key = (data.get("model") or DEFAULT_MODEL_KEY).strip().lower()
    image_b64 = data.get("image_b64")  # base64 image

    if not message:
        return jsonify({"error": "Empty message"}), 400

    messages = build_messages(history, message, image_b64)

    def stream():
        for line in generate_stream(preset_key, messages):
            yield line

    return Response(stream_with_context(stream()), mimetype='text/plain', content_type='text/event-stream')

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)