
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError(
        "Set SUPABASE_URL and SUPABASE_KEY in your .env file"
    )

supabase = create_client(supabase_url, supabase_key)

app = FastAPI(
    title="BE-03 Auth: Login & Protect",
    description="Authentication API using Supabase Auth",
    version="1.0.0",
)


@app.get("/public/info", tags=["Public"])
def public_info():
    return {"message": "Welcome stranger! This info is public."}
