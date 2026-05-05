import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Import your agent and system prompt from the graph file
from agent.graph import create_recommender_agent, SYSTEM_PROMPT

# Configure the Streamlit page
st.set_page_config(page_title="Electronics Recommender", layout="centered")
st.title("Electronics Recommender Assistant")
st.write("Ask me to find laptops, mice, headphones, or any other electronics!")

# Cache the agent initialization so it doesn't reload on every chat message
@st.cache_resource
def get_agent():
    return create_recommender_agent(model_name="qwen2.5:7b")

agent = get_agent()

# Initialize chat history in Streamlit session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capture user input from the chat box
if user_input := st.chat_input("What are you looking for today?"):
    
    # 1. Display the user's message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 2. Add user message to session state
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 3. Prepare the conversation history for LangGraph
    # We always start with the System Prompt
    langgraph_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            langgraph_messages.append(HumanMessage(content=msg["content"]))
        else:
            langgraph_messages.append(AIMessage(content=msg["content"]))

    # 4. Get the AI's response
    with st.chat_message("assistant"):
        with st.spinner("Searching the catalog..."):
            try:
                # Send the full conversation to your agent
                result = agent.invoke({"messages": langgraph_messages})
                
                # Extract the final answer
                final_answer = result["messages"][-1].content
                
                # Display the answer
                st.markdown(final_answer)
                
                # Save the answer to session state
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
            except Exception as e:
                st.error(f"Error connecting to local LLM: {e}. Is Ollama running?")