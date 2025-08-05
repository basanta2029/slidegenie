from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SlideGenie Test API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "SlideGenie API is running!", "status": "ok"}

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "service": "slidegenie-api"}

@app.get("/api/v1/test")
def test_endpoint():
    return {"test": "successful", "backend": "running"}