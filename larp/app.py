"""
default app creation
"""
import larp

app = larp.create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        'larp.app:app',
        host='0.0.0.0',
        port=44444,
        log_level='debug')
