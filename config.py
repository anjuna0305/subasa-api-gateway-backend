import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+aiomysql://subasa:your_password@localhost:3306/subasa",
)
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))
