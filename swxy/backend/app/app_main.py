from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from router import chat_rt, health_rt, knowledge_rt, session_rt, user_rt


app = FastAPI(
    title="GSK-POC 企业知识问答 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for api_router in (
    user_rt.router,
    knowledge_rt.router,
    session_rt.router,
    chat_rt.router,
    health_rt.router,
):
    app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
