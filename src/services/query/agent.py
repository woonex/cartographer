from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from tools.search_manual import search_manual
from tools.vehicle_state import vehicle_state

system_prompt = SystemMessage(
    "You are a helpful vehicle assistant. You have access to tools to answer questions about the user's vehicles. You must ground your answers in the outputs from the tools. If the tool searches do not provide useful information, directly tell the user. Do not attempt to use answers from memory."
)

tools = [
    search_manual,
    vehicle_state
]

model = ChatGroq(
    model="llama-3.1-8b-instant"
)

agent = create_agent(model=model, tools=tools, system_prompt=system_prompt)

def ask(question: str, vehicle: str) -> str:
    result = agent.invoke({
        "messages": [
            {
                "role": "system",
                "content": f"The user's active vehicle is currently {vehicle}.",
            },
            {
                "role": "user",
                "content": question,
            }
        ]
    })
    return result
