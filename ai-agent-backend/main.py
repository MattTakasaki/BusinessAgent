from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from oauth_router import oauth_router
from chat_router import chat_router
from memory_router import memory_router
from usage_router import usage_router
from admin_router import admin_router

load_dotenv()

app = FastAPI(title="AI Agent Platform")

# Add this block
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # add your production URL here later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(usage_router)
app.include_router(admin_router)