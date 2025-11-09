"""
Database service - Supabase client
"""

from supabase import create_client, Client
import os

# Initialize Supabase client
def get_supabase() -> Client:
    """Get Supabase client instance"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")

    return create_client(url, key)

# Singleton instance
supabase_client = None

def get_db() -> Client:
    """Get or create Supabase client singleton"""
    global supabase_client
    if supabase_client is None:
        supabase_client = get_supabase()
    return supabase_client
