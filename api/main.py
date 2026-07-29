from fastapi import FastAPI
app = FastAPI(title="Matchlens API")

@app.get("/")
def read_root():
    return{"status": "Matchlens API has been started succesfully"}

