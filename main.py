from fastapi import FastAPI


app = FastAPI(title="Document Intelligence Backend")

@app.get("/health", status_code=200)
def health():
    return {"status": "ok"}