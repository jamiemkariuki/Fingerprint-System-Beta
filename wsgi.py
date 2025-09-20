import os
from main import create_app

application = create_app()

if __name__ == "__main__":
    application.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5000))
    )
