from fastapi import FastAPI

app = FastAPI(
    title="Personalization Service",
    description="Сервис-заглушка",
    version="1.0.0",
)

@app.get("/health", status_code=200)
def health():
    return {"status": "ok", "service": "personalization"}