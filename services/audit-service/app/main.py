from fastapi import FastAPI

app = FastAPI(title="AuditService")

@app.get("/health")
def health():
    return {"status": "ok"}
