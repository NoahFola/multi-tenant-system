from fastapi import FastAPI

app = FastAPI(title="TenantUserService")

@app.get("/health")
def health():
    return {"status": "ok"}
