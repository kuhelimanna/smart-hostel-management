from langgraph.graph import StateGraph, START, END
from langchain.messages import AnyMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
import operator

from App.agents.hostel_agent import HostelAssistantAgent

class MessageState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

def should_continue(state: MessageState):
    messages = state["messages"]
    last_message = messages[-1]

    if getattr(last_message, "tool_calls", None):
        return "use_tools"

    return "end_workflow"

class HostelWorkflow:
    def __init__(self, mcp_tools=None):
        self.agent = HostelAssistantAgent(mcp_tools=mcp_tools)
        workflow_builder = StateGraph(MessageState)

        workflow_builder.add_node("brain_node", self.agent.run_llm)
        workflow_builder.add_node("action_node", self.agent.tool_node)

        workflow_builder.add_edge(START, "brain_node")
        workflow_builder.add_conditional_edges(
            "brain_node",
            should_continue,
            {
                "use_tools": "action_node",
                "end_workflow": END
            }
        )
        workflow_builder.add_edge("action_node", "brain_node")

        self.workflow = workflow_builder.compile()

    async def run_hostel_workflow(self, query: str) -> dict:
        result = await self.workflow.ainvoke(
            {
                "messages": [HumanMessage(content=query)]
            },
            config={"recursion_limit": 8}
        )
        return result

if __name__ == "__main__":
    import asyncio
    async def test():
        wf = HostelWorkflow()
        res = await wf.run_hostel_workflow("What is the curfew time for hostel students?")
        print("Response:", res["messages"][-1].content)
    asyncio.run(test())
