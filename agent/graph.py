import os
import sys

# 1. Force Python to look inside this specific folder first
current_folder = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_folder)

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Import directly from tools
from tools import search_catalog

# 2. Define the System Prompt globally
SYSTEM_PROMPT = """
You are an expert Electronics Recommender Assistant. 
Your goal is to help users find the best products based on their needs.

INSTRUCTIONS:
1. ALWAYS use the `search_catalog` tool when a user asks for a product, recommendation, or price.
2. Read the results from the tool and summarize them clearly for the user.
3. If the tool returns "Price unavailable", suggest that they check the latest price online.
4. Keep your responses conversational, helpful, and concise. Do not just dump the raw data.
5. If the user is just saying hello, greet them back and ask what kind of electronics they are looking for.
"""

def create_recommender_agent(model_name="qwen2.5:7b"):
    """Creates the LangGraph agent connected to a local Ollama instance."""
    
    llm = ChatOpenAI(
        model=model_name, 
        api_key="ollama", 
        base_url="http://localhost:11434/v1", 
        temperature=0.3 
    )

    tools = [search_catalog]

    # 3. We create the agent WITHOUT the modifier argument to avoid version errors
    agent_executor = create_react_agent(
        llm, 
        tools=tools
    )
    
    return agent_executor

if __name__ == "__main__":
    
    OLLAMA_MODEL = "qwen2.5:7b" 
    
    print("Initializing Agent. Connecting to local Ollama server...")
    app = create_recommender_agent(model_name=OLLAMA_MODEL)
    
    print("-" * 50)
    print("WELCOME TO THE ELECTRONICS RECOMMENDER")
    print("Type 'quit' or 'exit' to stop.")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['quit', 'exit']:
            print("Goodbye.")
            break
            
        if not user_input.strip():
            continue
            
        # 4. We inject the System Prompt directly into the message history here!
        messages = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_input)
            ]
        }
        
        print("Agent: ", end="", flush=True)
        
        try:
            result = app.invoke(messages)
            
            final_answer = result["messages"][-1].content
            print(final_answer + "\n")
            
        except Exception as e:
            print(f"\nError connecting to local LLM: {e}")
            print("Tip: Make sure the Ollama application is running in the background.")