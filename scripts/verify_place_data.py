"""Verify place data format matches database schema"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.db import get_db
from services.visit_seoul_api import parse_visit_seoul_place, get_place_detail
from services.place_parser import merge_place_data

load_dotenv()

def verify_place_data_sample():
    """Verify a sample place data matches schema"""
    db = get_db()
    
    # Get a sample place from database
    result = db.table("places").select("*").limit(1).execute()
    
    if not result.data or len(result.data) == 0:
        print("No places found in database. Please run collect_places.py first.")
        return
    
    sample_place = result.data[0]
    
    print("=" * 60)
    print("Database Schema vs Actual Data Verification")
    print("=" * 60)
    print("\nPlaces Table Schema:")
    print("  - id: UUID PRIMARY KEY")
    print("  - name: VARCHAR(255) NOT NULL UNIQUE")
    print("  - description: TEXT")
    print("  - category: VARCHAR(50)")
    print("  - address: VARCHAR(500)")
    print("  - district: VARCHAR(50)")
    print("  - latitude: DECIMAL(10, 8)")
    print("  - longitude: DECIMAL(11, 8)")
    print("  - image_url: TEXT")
    print("  - images: JSONB")
    print("  - metadata: JSONB")
    print("  - source: VARCHAR(20) DEFAULT 'manual'")
    print("  - is_active: BOOLEAN DEFAULT TRUE")
    print("  - view_count: INTEGER DEFAULT 0")
    print("  - created_at: TIMESTAMP")
    print("  - updated_at: TIMESTAMP")
    
    print("\n" + "=" * 60)
    print("Sample Place Data from Database:")
    print("=" * 60)
    
    for key, value in sample_place.items():
        value_type = type(value).__name__
        value_preview = str(value)
        if len(value_preview) > 100:
            value_preview = value_preview[:100] + "..."
        
        # Check for issues
        issues = []
        if key == "name" and not value:
            issues.append(" REQUIRED FIELD IS NULL")
        if key == "latitude" and value is None:
            issues.append("  NULL (may cause issues)")
        if key == "longitude" and value is None:
            issues.append("  NULL (may cause issues)")
        if key == "district" and value is None:
            issues.append("  NULL (should be extracted from address)")
        if key == "images" and value and not isinstance(value, list):
            issues.append("  Should be list/array")
        if key == "metadata" and value and not isinstance(value, dict):
            issues.append("  Should be dict/object")
        
        status = "OK" if not issues else " ".join(issues)
        print(f"  {key:20} | {value_type:15} | {status}")
        print(f"    Value: {value_preview}")
    
    print("\n" + "=" * 60)
    print("Verification Summary:")
    print("=" * 60)
    
    # Check required fields
    required_fields = ["name"]
    missing_required = [f for f in required_fields if not sample_place.get(f)]
    
    if missing_required:
        print(f"Missing required fields: {missing_required}")
    else:
        print("All required fields present")
    
    # Check data types
    type_checks = {
        "name": str,
        "description": (str, type(None)),
        "category": (str, type(None)),
        "address": (str, type(None)),
        "district": (str, type(None)),
        "latitude": (float, int, type(None)),
        "longitude": (float, int, type(None)),
        "image_url": (str, type(None)),
        "images": (list, type(None)),
        "metadata": (dict, type(None)),
        "source": str,
        "is_active": bool,
        "view_count": int
    }
    
    type_issues = []
    for field, expected_type in type_checks.items():
        if field in sample_place:
            value = sample_place[field]
            if value is not None:
                if not isinstance(value, expected_type):
                    type_issues.append(f"{field}: expected {expected_type}, got {type(value)}")
    
    if type_issues:
        print(f"  Type issues found:")
        for issue in type_issues:
            print(f"    - {issue}")
    else:
        print(" All data types match schema")
    
    # Check constraints
    print("\nConstraint Checks:")
    if sample_place.get("source") not in ["manual", "tour_api", "visit_seoul", "both"]:
        print(f"  source value '{sample_place.get('source')}' not in allowed values")
    else:
        print(" source constraint satisfied")
    
    if sample_place.get("name") and len(sample_place["name"]) > 255:
        print(f"  name exceeds VARCHAR(255) limit: {len(sample_place['name'])} chars")
    else:
        print(" name length within limit")
    
    if sample_place.get("address") and len(sample_place["address"]) > 500:
        print(f"  address exceeds VARCHAR(500) limit: {len(sample_place['address'])} chars")
    else:
        print(" address length within limit")
    
    if sample_place.get("category") and len(sample_place["category"]) > 50:
        print(f"  category exceeds VARCHAR(50) limit: {len(sample_place['category'])} chars")
    else:
        print(" category length within limit")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    verify_place_data_sample()
