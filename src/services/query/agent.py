from dotenv import load_dotenv
from groq import BadRequestError
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode

from tools.get_specification_info import get_specification_info
from tools.search_manual import search_manual
from tools.vehicle_state import vehicle_state

load_dotenv()

system_prompt = SystemMessage(
    "You are a helpful vehicle assistant. "
    "You have access to tools to answer questions about the user's vehicles. "
    "You must ground your answers in the outputs from the tools. "
    "If the tool searches do not provide useful information, directly tell the user. "
    "NEVER make up an answer. If you can't find the info in all of the tool calls, "
    "respond with \"I couldn't find that information\""
)

tools = [search_manual, vehicle_state, get_specification_info]

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


def ask(question: str, vehicle: str) -> str:
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"[Context: The user's active vehicle is currently {vehicle}.]\n\n{question}",
                }
            ]
        }
    )
    print(result)
    return result["messages"][-1].content
