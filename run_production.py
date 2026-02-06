import os
from waitress import serve
from wsgi import application

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080")) # Default to 8080 for production if not set
    
    print(f"Starting Production Server on {host}:{port}...")
    # Threads default is 4, which is reasonable. 
    # connection_limit default is 75.
    serve(application, host=host, port=port)
