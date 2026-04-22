# main.py
from fastapi import FastAPI
from dotenv import load_dotenv
from oauth_router import oauth_router

load_dotenv()
app = FastAPI()
app.include_router(oauth_router)