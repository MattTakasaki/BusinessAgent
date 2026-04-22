from fastapi import FastAPI
from dotenv import load_dotenv
from oauth_router import oauth_router
from chat_router import chat_router
from memory_router import memory_router
from usage_router import usage_router

load_dotenv()

app = FastAPI(title="AI Agent Platform")
app.include_router(oauth_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(usage_router)