from fastapi import FastAPI

app = FastAPI(title="AuthService")

@app.get("/health")
def health():
    return {"status": "ok"}
