from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "OK"}

@app.get("/ping")
def ping():
    print("PING RECEIVED")
    return {"message": "pong"}
