from fastapi import FastAPI

app = FastAPI(
    title="Project Vigilance",
    description="AI-assisted Anti-Money-Laundering Investigation Platform",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "project-vigilance"}

@app.get("/")
def root():
    return {
        "project": "Project Vigilance",
        "message": "AML investigation platform is running",
    }
