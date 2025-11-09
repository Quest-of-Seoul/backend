"""
Create get_user_points function using direct PostgreSQL connection
"""
import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Parse Supabase URL to get database connection info
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Extract project ref from URL
# URL format: https://[project_ref].supabase.co
project_ref = SUPABASE_URL.split("//")[1].split(".")[0]

# Construct PostgreSQL connection string
# Supabase PostgreSQL connection format
DB_HOST = f"db.{project_ref}.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"

print(f"[*] Enter your Supabase database password")
print(f"    (Find it in Supabase Dashboard > Settings > Database > Connection string)")
DB_PASSWORD = input("Password: ")

print(f"\n[*] Connecting to PostgreSQL: {DB_HOST}")

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    cursor = conn.cursor()

    print("[*] Creating get_user_points function...")

    # Create the function
    create_function_sql = """
    CREATE OR REPLACE FUNCTION get_user_points(user_uuid uuid)
    RETURNS int AS $$
      SELECT COALESCE(SUM(value), 0)::int FROM points WHERE user_id = user_uuid;
    $$ LANGUAGE sql STABLE;
    """

    cursor.execute(create_function_sql)
    conn.commit()

    print("[OK] Function created successfully!")

    # Test the function
    print("\n[TEST] Testing the function...")
    test_uuid = "3ad218e3-a3a0-4e3a-bde1-1b2c6d53081f"
    cursor.execute(f"SELECT get_user_points('{test_uuid}'::uuid)")
    result = cursor.fetchone()
    print(f"[OK] Function test successful! Points for user: {result[0]}")

    cursor.close()
    conn.close()

    print("\n[DONE] Function created! Please restart your backend server.")

except psycopg2.Error as e:
    print(f"[ERROR] Database error: {e}")
    print("\nAlternative: Run this SQL in Supabase SQL Editor:")
    print(create_function_sql)
except Exception as e:
    print(f"[ERROR] Error: {e}")
