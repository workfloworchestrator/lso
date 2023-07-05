"""
default app creation
"""
import lso

app = lso.create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("lso.app:app", host="0.0.0.0", port=44444, log_level="debug")
