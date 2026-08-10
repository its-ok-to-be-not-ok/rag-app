from langfuse.langchain import CallbackHandler
from langchain_openai import ChatOpenAI

# Test connection
handler = CallbackHandler()

llm = ChatOpenAI(model="gpt-3.5-turbo")
response = llm.invoke(
    "Say hello", 
    config={"callbacks": [handler]}
)

handler.flush()  # Force send
print("✅ Test complete - check Langfuse UI")