# import asyncio
# from typing import List, TypedDict
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langchain_core.messages import HumanMessage
# from langgraph.graph import StateGraph, START, END
# from langgraph.prebuilt import create_react_agent
# from langchain_groq import ChatGroq

# class WorkflowState(TypedDict, total=False):
#     query: str
#     response: List
#     was_helpful: str
#     wants_escalation: str

# async def main():
#     # Getting tools from MCP server
#     client = MultiServerMCPClient(
#         {
#             "math": {
#                 "command": "python",
#                 "args": ["C:/Users/priti/OneDrive/Desktop/Hitachi/mcp_langgraph_integration/new/servers/math_server_mcp.py"],
#                 "transport": "stdio",
#             },
#             "document_reader":{
#                 "command": "python",
#                 "args": ["C:/Users/priti/OneDrive/Desktop/Hitachi/mcp_langgraph_integration/new/servers/document_reader_tool.py"],
#                 "transport":"stdio"
#             }
#         }
#     )
#     tools = await client.get_tools()
#     print('The following tools were fetched from MCP server',tools)
   
#     agent = create_react_agent(
#         ChatGroq(groq_api_key='', model_name='gemma2-9b-it'),
#         tools=tools,
#     )

#     async def handle_query(state):
#         response = await agent.ainvoke({"messages": [HumanMessage(content=state["query"])]})
#         state["response"] = response["messages"]
#         return state
    
#     async def ask_was_helpful(state):
#         print("\nAgent Response:")
#         for msg in state["response"]:
#             print("-", msg.content)
#         answer = input("\nWas this helpful? (yes/no): ").strip().lower()
#         state["was_helpful"] = answer
#         return state
    
#     async def ask_escalate(state):
#         if state["was_helpful"] == "yes":
#             return {"next": "end"}
#         answer = input("Would you like to escalate this to human IT support? (yes/no): ").strip().lower()
#         state["wants_escalation"] = answer
#         return {"next": "escalate" if answer == "yes" else "end"}
    
#     async def escalate_to_gmail(state):
#         print("Sending email to IT support...")
#         return {"next": "end"}
    
#     async def end_state(state):
#         print("Conversation ended.")
#         return state
    
#     workflow = StateGraph(WorkflowState)                                                                                                                                                                                                                                                                                                                                                                        
#     workflow.add_node("handle_query", handle_query)
#     workflow.add_node("ask_was_helpful", ask_was_helpful)
#     workflow.add_node("ask_escalate", ask_escalate)
#     workflow.add_node("escalate", escalate_to_gmail)
#     workflow.add_node("end", end_state)

#     workflow.set_entry_point("handle_query")
#     workflow.add_edge("handle_query", "ask_was_helpful")
#     workflow.add_edge("ask_was_helpful", "ask_escalate")
#     workflow.add_conditional_edges("ask_escalate", lambda state: state["next"], {
#         "escalate": "escalate",
#         "end": END
#     })
#     workflow.add_edge("escalate", "end")

#     response = await agent.ainvoke(
#     {"messages": [HumanMessage(content="how do I fix my hardware issue")]}
#     )
#     print("Response:", response['messages'])

#     graph = workflow.compile()
#     # initial_state = {"query": "how do I fix my hardware issue"}
#     # await graph.ainvoke(initial_state)


# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
from typing import Annotated, Sequence, TypedDict, Literal
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
openAIKey=os.getenv("OPEN_AI_KEY")

class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]

async def main():
    client = MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                "args": ["C:/Users/priti/OneDrive/Desktop/Hitachi/mcp_langgraph_integration/new/servers/math_server_mcp.py"],
                "transport": "stdio",
            },
            "document_reader": {
                "command": "python",
                "args": ["C:/Users/priti/OneDrive/Desktop/Hitachi/mcp_langgraph_integration/new/servers/document_reader_tool.py"],
                "transport": "stdio"
            },
        }
    )
    tools = await client.get_tools()
    print("The following tools were fetched from MCP server:", tools)
    
    model = ChatOpenAI(
        openai_api_key=openAIKey,      
        model_name="gpt-4o",             
        temperature=0.7,                
    ).bind_tools(tools)

    async def handle_query(state: AgentState) -> AgentState:
        system_prompt = SystemMessage(content="You are a support assistant. Your job is to answer user issues strictly using documentation provided via tools. If information is not found in the docs, respond with 'I don't have enough documentation to answer that.'")
        response = await model.ainvoke([system_prompt] + state["messages"])
        print("\nAgent Response:", response)
        return {"messages": state["messages"] + [response]}

    def should_continue(state: AgentState) -> Literal["end", "continue"]:
        last_message = state["messages"][-1]
        return "continue" if getattr(last_message, "tool_calls", None) else "end"

    def ask_another_query(state: AgentState) -> Literal["ask", "no"]:
        while True:
            answer = input("\nWould you like to ask another question? (yes/no): ").strip().lower()
            if answer in ["yes", "no"]:
                return "ask" if answer == "yes" else "no"
            print("Please enter yes or no.")

    def get_new_query(state: AgentState) -> AgentState:
        query = input("\nPlease enter your next question: ").strip()
        return {"messages": state["messages"] + [HumanMessage(content=query)]}

    def ask_was_helpful(state: AgentState) -> Literal["end", "continue"]:
        while True:
            answer = input("\nWas this helpful? (yes/no): ").strip().lower()
            if answer in ["yes", "no"]:
                return "end" if answer == "yes" else "continue"
            print("Please enter yes or no.")

    def ask_escalate(state: AgentState) -> Literal["end", "continue"]:
        while True:
            answer = input("\nWould you like to escalate this to human IT support? (yes/no): ").strip().lower()
            if answer in ["yes", "no"]:
                return "continue" if answer == "yes" else "end"
            print("Please enter yes or no.")

    def escalate_to_gmail(state: AgentState):
        print("\nSending email to IT support...")

    def end_state(state: AgentState):
        print("\nConversation ended.")
        return state

    graph = StateGraph(AgentState)

    graph.add_node("handle_query", handle_query)
    graph.add_node("tool_execution", ToolNode(tools=tools))
    graph.add_node("ask_another", ask_another_query)
    graph.add_node("get_query", get_new_query)
    graph.add_node("ask_was_helpful", ask_was_helpful)
    graph.add_node("ask_escalate", ask_escalate)
    graph.add_node("escalate", escalate_to_gmail)
    graph.add_node("end", end_state)
    
    # routers
    graph.add_node("router0", lambda state: state)
    graph.add_node("router1", lambda state: state)
    graph.add_node("router2", lambda state: state)

    graph.set_entry_point("handle_query")

    graph.add_conditional_edges(
        "handle_query",
        should_continue,
        {
            "continue": "tool_execution",
            "end": "router0",
        }
    )

    graph.add_edge("tool_execution", "router0")

    graph.add_conditional_edges(
        "router0",
        ask_another_query,
        {
            "ask": "get_query",
            "no": "router1"
        }
    )

    graph.add_edge("get_query", "handle_query")

    graph.add_conditional_edges(
        "router1",
        ask_was_helpful,
        {
            "end": "end",
            "continue": "router2",
        }
    )

    graph.add_conditional_edges(
        "router2",
        ask_escalate,
        {
            "end": "end",
            "continue": "escalate",
        }
    )

    graph.add_edge("escalate", "end")
    graph.add_edge("end", END)

    app = graph.compile()

    # async def print_stream(stream):
    #     for s in stream:
    #         message = s["messages"][-1]
    #         if isinstance(message, tuple):
    #             print(message)
    #         else:
    #             message.pretty_print()

    # inputs = {"messages": [HumanMessage(content="how do I fix my hardware issue.")]}
    # print_stream(app.stream(inputs, stream_mode="values"))

    async for chunk, metadata in app.astream(
        {"messages": [HumanMessage(content="My device's screen is not working.")]},
        stream_mode="messages", 
    ):
        if hasattr(chunk, "content") and chunk.content:
            print(chunk, end="|", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
