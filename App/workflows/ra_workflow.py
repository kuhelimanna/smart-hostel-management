from langgraph.graph import StateGraph, START, END
from langchain.messages import AnyMessage, HumanMessage

from typing_extensions import TypedDict, Annotated

import operator

from App.agents.ra_agent import ResearchAssistantAgent

class MessageState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

def should_continue(state: MessageState):
    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "use_tools"

    return "end_workflow"

class ResearchAssistantWorkflow:
    def __init__(self, mcp_tools):
        workflow_builder = StateGraph(MessageState)

        workflow_builder.add_node("brain_node", 
                                ResearchAssistantAgent(mcp_tools).run_llm)

        workflow_builder.add_node("action_node",
                                ResearchAssistantAgent(mcp_tools).tool_node)

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

    async def run_ra_workflow(self, query: str) -> dict:
       
        result = await self.workflow.ainvoke(
            {
                "messages": [HumanMessage(content=query)]
            },
            config={"recursion_limit": 10}
        )

        return result

if __name__ == "__main__":
    # workflow = TeachingAssistantWorkflow()
    # result = workflow.run_ta_workflow("What are pointers?")
    # print("\n\n-------------------FINAL ANSWER--------------\n\n")
    # print(result)
    pass