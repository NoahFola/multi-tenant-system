from fastapi import FastAPI

app = FastAPI(title="WorkflowService")

@app.get("/health")
def health():
    return {"status": "ok"}
