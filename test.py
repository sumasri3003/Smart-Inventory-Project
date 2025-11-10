from app.db import SessionLocal

try:
    db = SessionLocal()
    print(" DB Connection Successful")
except Exception as e:
    print(" DB Error:", e)