import json

from fastapi import Depends, FastAPI
from pydantic import BaseModel
import gradio as gr
import httpx

from settings_frontend import Settings, get_settings

settings = get_settings()
app = FastAPI()


@app.get("/health")
def health():
    """If the server is alive"""
    return {"status": "ok"}


@app.get("/ready")
def ready(settings: Settings = Depends(get_settings)):
    """If the server is ready to process ingestion

    returns:
    200 if okay
    503 if service unavailable
    """
    return {"status": "ready"}


@app.get("/available-vehicles")
def get_available_vehicles() -> list[str]:
    """Gets available vehicles for the user"""
    response = httpx.get(
        f"{settings.vehicle_library_url}/vehicles",
    )
    response.raise_for_status()
    return response.json()


def _render(tool_sections: list[str], answer: str) -> str:
    parts = list(tool_sections)
    if answer:
        parts.append(answer)
    return "\n".join(parts)


def respond(message: str, history: list, vehicle: str):
    history = list(history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    yield "", history

    tool_sections: list[str] = []
    answer = ""

    with httpx.stream(
        "POST",
        f"{settings.query_url}/query/stream",
        json={"vehicle": vehicle, "question": message},
        timeout=120,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])

            if event["type"] == "tool_call":
                args_json = json.dumps(event["args"], indent=2)
                tool_sections.append(
                    f"<details><summary>🔧 {event['name']}</summary>\n\n"
                    f"```json\n{args_json}\n```\n\n</details>"
                )

            elif event["type"] == "tool_result":
                tool_sections.append(
                    f"<details><summary>📥 Result from {event['name']}</summary>\n\n"
                    f"```\n{event['content']}\n```\n\n</details>"
                )

            elif event["type"] == "answer_token":
                answer += event["content"]

            elif event["type"] == "error":
                answer = f"Error: {event['content']}"

            elif event["type"] == "done":
                break

            history[-1]["content"] = _render(tool_sections, answer)
            yield "", history


def on_vehicle_select(vehicle: str):
    enabled = bool(vehicle)
    placeholder = "Ask a question..." if enabled else "Select a vehicle above to begin..."
    return gr.Textbox(interactive=enabled, placeholder=placeholder), gr.Button(interactive=enabled)


with gr.Blocks() as gradio_app:
    vehicle_dd = gr.Dropdown(label="Vehicle", interactive=True, allow_custom_value=True)
    chatbot = gr.Chatbot()
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Select a vehicle above to begin...",
            interactive=False,
            show_label=False,
            scale=9,
        )
        submit = gr.Button("Send", interactive=False, scale=1)

    vehicle_dd.change(on_vehicle_select, vehicle_dd, [msg, submit])
    submit.click(respond, [msg, chatbot, vehicle_dd], [msg, chatbot])
    msg.submit(respond, [msg, chatbot, vehicle_dd], [msg, chatbot])

    def load_vehicles():
        return gr.Dropdown(choices=get_available_vehicles())

    gradio_app.load(load_vehicles, outputs=vehicle_dd)

app = gr.mount_gradio_app(app, gradio_app, path="/")
