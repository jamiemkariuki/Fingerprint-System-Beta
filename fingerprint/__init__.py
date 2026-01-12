# Lightweight wrapper to expose the app factory with a clean import path.
try:
    from src.main import create_app as create_app
except Exception:
    try:
        from main import create_app as create_app
    except Exception as e:
        raise ImportError("Unable to import app factory from src.main or main") from e
