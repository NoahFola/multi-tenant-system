from fastapi import FastAPI

app = FastAPI(title="NotificationService")

@app.get("/health")
def health():
    return {"status": "ok"}
