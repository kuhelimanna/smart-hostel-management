from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.messages import SystemMessage, ToolMessage, AIMessage

import os
from dotenv import load_dotenv

from App.services.rag_service import EmbeddingService

load_dotenv()

@tool
def retriever(query: str) -> list:
    """
    This tool is used to retrieve data from a pdf which answer questions,
    on C programming language. This tool retrieves the excat curriculum taught in DSTAM.
    Use this tool to gain information for C programming curriculum of DSATM.

    Input:
    Query (str): The query given /enhanced by the AI Agent

    Output:
    Chunks (list): The chunks retrieved from vectorDB
    """
    embedding_service = EmbeddingService()
    context = embedding_service.retrieve_from_pdf(query)

    return context

web_search = DuckDuckGoSearchRun()

class TeachingAssistantAgent:
    def __init__(self):
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.7,
            max_tokens=1024,
            api_key=os.getenv("GROQ_API_KEY")
        )

        tools_list = [retriever, web_search]

        self.llm_with_tools = llm.bind_tools(tools_list)


        self.tools_by_name = {tool.name: tool for tool in tools_list}

    def run_llm(self, state: dict) -> dict: # Brain
        result = {
            "messages": [
                self.llm_with_tools.invoke(
                    [
                        SystemMessage(
                    content="""
                    You are a helpful Teaching Assistant for the C Programming language at DSTAM, Bangalore.
                    
                    You must answer all questions keeping in mind that the answers are to be given from the 
                    context of the DSTAM curriculum C Programming Course. You have access to the `retriever` 
                    tool. Any information not available in the pdf tool is to be attained using the `web_search` tool.
                    
                    Strictly maintain that you are a C programming teaching agent only. Do not answer irrelevant questions.
                    
                    Output Format:
                    1. [Answer 1]
                    2. [Answer 2]
                    3. [Answer 3]
                    """
                        )
                    ]
                    + state['messages']
                )
            ],
            "llm_calls": state.get('llm_calls', 0) + 1
        }

        print("\n\n-----------------------AI MESSAGE -------------------\n\n")
        print(result)

        return result

    def tool_node(self, state: dict) -> dict: # Action
        result = []

        for tool_call in state['messages'][-1].tool_calls:

            if 'self' in tool_call["args"]:
                del tool_call["args"]['self']

            tool = self.tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])

            if isinstance(observation, list):
                content_string = "\n".join(observation)
            else:
                content_string = str(observation)

            result.append(
                ToolMessage(
                    content=content_string,
                    tool_call_id=tool_call["id"]
                )
            )

        print("\n\n-----------------------Tool MESSAGE -------------------\n\n")
        print(result)
        
        return {"messages": result}

if __name__ ==  "__main__":
    # query = input("Enter your query: ")
    # print(run_llm(query))

    chunk = retriever.invoke("What is a pointer?")
    print("\n\nCHUNKS RETRIEVED ")
    print(chunk)
    print("\n\n")

    search = web_search.invoke("LA Olympics 2028")
    print(search)