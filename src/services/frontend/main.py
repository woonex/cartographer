import json

import gradio as gr
import httpx
from fastapi import Depends, FastAPI

from settings_frontend import Settings, get_settings

settings = get_settings()
app = FastAPI()


def check_query_ready() -> bool:
    try:
        resp = httpx.get(f"{settings.query_url}/ready", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


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


def _render(tool_names: list[str], tool_content: str, answer: str, streaming: bool) -> str:
    parts = []
    if tool_content:
        open_attr = " open" if streaming else ""
        unique_names = list(dict.fromkeys(tool_names))
        summary = f"Steps taken ({', '.join(unique_names)})"
        parts.append(f"<details{open_attr}><summary>{summary}</summary>\n\n{tool_content}</details>")
    if tool_content and answer:
        parts.append("\n---\n")
    if answer:
        parts.append(answer)
    return "\n".join(parts)


def respond(message: str, history: list, vehicle: str):
    history = list(history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    yield "", history

    tool_names: list[str] = []
    tool_content = ""
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

            if event["type"] == "reasoning":
                tool_content += f"*{event['content']}*\n\n"

            elif event["type"] == "tool_call":
                tool_names.append(event["name"])
                args_json = json.dumps(event["args"], indent=2)
                tool_content += f"**{event['name']}**\n\nInput:\n```json\n{args_json}\n```\n\n"

            elif event["type"] == "tool_result":
                try:
                    result_str = json.dumps(json.loads(event["content"]), indent=2)
                except (json.JSONDecodeError, TypeError):
                    result_str = event["content"]
                tool_content += f"Result:\n```json\n{result_str}\n```\n\n"

            elif event["type"] == "answer_token":
                answer += event["content"]

            elif event["type"] == "error":
                answer = f"Error: {event['content']}"

            elif event["type"] == "done":
                break

            history[-1]["content"] = _render(tool_names, tool_content, answer, streaming=not answer)
            yield "", history

    # Final render: collapse the steps block now that we have the answer
    history[-1]["content"] = _render(tool_names, tool_content, answer, streaming=False)
    yield "", history


def on_vehicle_select(vehicle: str):
    if not check_query_ready():
        return gr.Textbox(interactive=False), gr.Button(interactive=False)
    enabled = bool(vehicle)
    placeholder = "Ask a question..." if enabled else "Select a vehicle above to begin..."
    return gr.Textbox(interactive=enabled, placeholder=placeholder), gr.Button(interactive=enabled)


def on_ready_tick(vehicle: str):
    """Polls /ready and updates UI state. Stops timer once service is up."""
    ready = check_query_ready()
    if ready:
        has_vehicle = bool(vehicle)
        placeholder = "Ask a question..." if has_vehicle else "Select a vehicle above to begin..."
        return (
            gr.Markdown(visible=False),
            gr.Textbox(interactive=has_vehicle, placeholder=placeholder),
            gr.Button(interactive=has_vehicle),
            gr.Timer(active=False),
        )
    return (
        gr.Markdown("Query service is starting up, please wait...", visible=True),
        gr.Textbox(interactive=False),
        gr.Button(interactive=False),
        gr.Timer(active=True),
    )


with gr.Blocks() as gradio_app:
    status_md = gr.Markdown("Query service is starting up, please wait...", visible=True)
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

    poll_timer = gr.Timer(2.0, active=True)
    poll_timer.tick(on_ready_tick, inputs=[vehicle_dd], outputs=[status_md, msg, submit, poll_timer])

    vehicle_dd.change(on_vehicle_select, vehicle_dd, [msg, submit])
    submit.click(respond, [msg, chatbot, vehicle_dd], [msg, chatbot])
    msg.submit(respond, [msg, chatbot, vehicle_dd], [msg, chatbot])

    def load_vehicles():
        return gr.Dropdown(choices=get_available_vehicles())

    gradio_app.load(load_vehicles, outputs=vehicle_dd)
    gradio_app.load(on_ready_tick, inputs=[vehicle_dd], outputs=[status_md, msg, submit, poll_timer])

app = gr.mount_gradio_app(app, gradio_app, path="/")
