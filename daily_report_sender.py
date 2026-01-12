try:
    from src.main.utils.email import generate_and_send_reports
except Exception:
    from main.utils.email import generate_and_send_reports

if __name__ == "__main__":
    generate_and_send_reports()
