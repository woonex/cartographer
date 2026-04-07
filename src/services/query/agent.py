from typing import AsyncGenerator

from dotenv import load_dotenv
from groq import BadRequestError
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode

from tools.get_maintenance_schedule import get_maintenance_schedule
from tools.get_specification_info import get_specification_info
from tools.search_manual import search_manual
from tools.vehicle_state import vehicle_state

load_dotenv()

system_prompt = SystemMessage(
    "You are a helpful vehicle assistant. "
    "You have access to tools to answer questions about the user's vehicles. "
    "For vehicle-related questions, always use your tools and ground your answers in their outputs. "
    "NEVER make up vehicle information. If the tools do not return useful information, "
    "respond with \"I couldn't find that information\". "
    "Answer the question directly and concisely. "
    "Do not add trailing suggestions, offers for follow-up, or phrases like 'let me know if you need more'. "
    "Only answer questions about vehicles, their manuals, specifications, and maintenance. "
    "If the user asks about anything else (coding, general knowledge, personal advice, etc.), "
    "respond with \"I can only help with vehicle-related questions.\""
)

tools = [search_manual, vehicle_state, get_specification_info, get_maintenance_schedule]

model = ChatGroq(model="openai/gpt-oss-120b").bind_tools(tools)

tool_node = ToolNode(tools, handle_tool_errors=True)


def call_model(state: MessagesState):
    messages = [system_prompt] + state["messages"]
    try:
        response = model.invoke(messages)
    except BadRequestError:
        response = AIMessage(
            content="I'm having trouble processing that request. "
            "Could you try rephrasing your question?"
        )
    return {"messages": [response]}


def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

agent = graph.compile()


_MAX_HISTORY = 10


def ask(question: str, vehicle: str, history: list[dict] | None = None) -> str:
    prior = (history or [])[-_MAX_HISTORY:]
    current = {
        "role": "user",
        "content": f"[Context: The user's active vehicle is currently {vehicle}.]\n\n{question}",
    }
    try:
        result = agent.invoke({"messages": prior + [current]}, config={"recursion_limit": 10})
        return result["messages"][-1].content
    except GraphRecursionError:
        return "I wasn't able to find enough information to answer that. Please try asking in a different way."


async def ask_stream(question: str, vehicle: str, history: list[dict] | None = None) -> AsyncGenerator[dict, None]:
    prior = (history or [])[-_MAX_HISTORY:]
    input_data = {
        "messages": prior + [{
            "role": "user",
            "content": f"[Context: The user's active vehicle is currently {vehicle}.]\n\n{question}",
        }]
    }
    try:
        async for event in agent.astream_events(input_data, version="v2", config={"recursion_limit": 10}):
            kind = event["event"]

            if kind == "on_tool_start":
                yield {
                    "type": "tool_call",
                    "name": event["name"],
                    "args": event["data"].get("input", {}),
                }

            elif kind == "on_tool_end":
                output = event["data"].get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                yield {
                    "type": "tool_result",
                    "name": event["name"],
                    "content": str(output),
                }

            elif kind == "on_chat_model_end":
                response = event["data"].get("output")
                if response:
                    reasoning = response.additional_kwargs.get("reasoning_content", "")
                    if reasoning:
                        yield {"type": "reasoning", "content": reasoning}

            elif kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    yield {"type": "answer_token", "content": chunk.content}

    except GraphRecursionError:
        yield {"type": "answer_token", "content": "I wasn't able to find enough information to answer that. Please try asking in a different way."}

    yield {"type": "done"}
