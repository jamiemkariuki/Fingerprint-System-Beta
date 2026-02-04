import sys
import traceback

print("Python Path:", sys.path)

try:
    print("Attempting to import src.main...")
    import src.main
    print("Successfully imported src.main")
    
    from src.main import create_app
    print("Successfully imported create_app")
    
    app = create_app()
    print("Successfully created app")
except Exception:
    traceback.print_exc()
