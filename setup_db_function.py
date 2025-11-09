"""
Temporary script to create get_user_points function in Supabase
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print(f"[*] Connecting to Supabase: {SUPABASE_URL}")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# SQL to create the function
create_function_sql = """
CREATE OR REPLACE FUNCTION get_user_points(user_uuid uuid)
RETURNS int AS $$
  SELECT COALESCE(SUM(value), 0)::int FROM points WHERE user_id = user_uuid;
$$ LANGUAGE sql STABLE;
"""

print("[*] Creating get_user_points function...")

try:
    # Execute the SQL using rpc with the query method
    result = supabase.rpc('exec_sql', {'query': create_function_sql}).execute()
    print("[OK] Function created successfully!")
except Exception as e:
    # If rpc doesn't work, try using postgrest directly
    print(f"[WARNING] RPC method failed: {e}")
    print("[*] Trying alternative method with raw SQL...")

    try:
        # Use the REST API directly to execute SQL
        response = supabase.postgrest.session.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            json={"query": create_function_sql},
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 200:
            print("[OK] Function created successfully!")
        else:
            print(f"[ERROR] Error: {response.status_code} - {response.text}")
            print("\n[NOTE] Please run this SQL manually in Supabase SQL Editor:")
            print(create_function_sql)
    except Exception as e2:
        print(f"[ERROR] Alternative method also failed: {e2}")
        print("\n[NOTE] Please run this SQL manually in Supabase SQL Editor:")
        print(create_function_sql)

# Test the function
print("\n[TEST] Testing the function...")
try:
    test_uuid = "3ad218e3-a3a0-4e3a-bde1-1b2c6d53081f"
    result = supabase.rpc("get_user_points", {"user_uuid": test_uuid}).execute()
    print(f"[OK] Function test successful! Points for user: {result.data}")
except Exception as e:
    print(f"[WARNING] Function test failed: {e}")
    print("This is normal if the function was just created. Try restarting your backend server.")

print("\n[DONE] Please restart your backend server now.")
