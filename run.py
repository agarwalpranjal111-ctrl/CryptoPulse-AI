"""Start the dashboard:  python run.py   then open http://localhost:5000"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False, log_level="info")
