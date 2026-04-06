import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Conn string from .env comment
conn_str = "postgresql://postgres:mySecurePass123@sb_domain.aichieve.net:5434/postgres"

print(f"Connecting to {conn_str}...")
try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"Success: {cur.fetchone()}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to connect: {e}")

# Try with localhost if port is mapped?
# No, let's try with SB_DOMAIN_BUILDOMAIN_COM if possible
conn_str_2 = "postgresql://postgres:mySecurePass123@sbdomain.buildomain.com:54322/postgres"
print(f"Connecting to {conn_str_2}...")
try:
    conn = psycopg2.connect(conn_str_2)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"Success: {cur.fetchone()}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to connect: {e}")
