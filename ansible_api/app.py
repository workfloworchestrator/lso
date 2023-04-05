"""
default app creation
"""
import ansible_api

app = ansible_api.create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        'ansible_api.app:app',
        host='0.0.0.0',
        port=44444,
        log_level='debug')
