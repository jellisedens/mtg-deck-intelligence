from database.session import SessionLocal
from sqlalchemy import text
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"])
new_hash = pwd.hash("TempPass2026!")
db = SessionLocal()
result = db.execute(text("SELECT id, email FROM users WHERE email = :e"), {"e": "westin.edwards@gmail.com"})
user = result.fetchone()
if user:
    db.execute(text("UPDATE users SET password_hash = :h WHERE email = :e"), {"h": new_hash, "e": "westin.edwards@gmail.com"})
    db.commit()
    print(f"Password reset for {user.email}")
else:
    print("User not found")
db.close()