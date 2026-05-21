from fastapi import FastAPI
from app.routes.chat import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def home():
    return {
        "message": "ChargeGrid AI Online"
    }