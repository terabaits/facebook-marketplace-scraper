#!/usr/bin/env python3
"""
Verification script for listing versioning migration.

Checks that all required columns, constraints, and tables were created correctly.
Run after migration to confirm everything is in place.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text, inspect
from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.logger import get_logger

logger = get_logger("verification")


def check_column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_constraint_exists(inspector, table_name: str, constraint_name: str) -> bool:
    """Check if a specific constraint exists."""
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def check_composite_constraint_exists(inspector, table_name: str, columns: list) -> bool:
    """Check if a composite unique constraint exists on specific columns."""
    constraints = inspector.get_unique_constraints(table_name)
    for c in constraints:
        if set(c['column_names']) == set(columns):
            return True
    return False


def check_index_exists(inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def check_table_exists(inspector, table_name: str) -> bool:
    """Check if a table exists."""
    return table_name in inspector.get_table_names()


def get_row_count(session, table_name: str) -> int:
    """Get the row count for a table."""
    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()
    return result[0] if result else 0


def verify_table(inspector, session, table_name: str, id_column: str = "listing_id") -> dict:
    """Verify a single table has all required components."""
    results = {
        "table": table_name,
        "exists": check_table_exists(inspector, table_name),
        "version_column": False,
        "fingerprint_column": False,
        "composite_unique": False,
        "version_index": False,
        "fingerprint_index": False,
        "row_count": 0,
        "null_versions": None,
        "errors": []
    }
    
    if not results["exists"]:
        results["errors"].append(f"Table {table_name} does not exist")
        return results
    
    # Check columns
    results["version_column"] = check_column_exists(inspector, table_name, "version_number")
    results["fingerprint_column"] = check_column_exists(inspector, table_name, "content_fingerprint")
    
    # Check composite unique constraint
    results["composite_unique"] = check_composite_constraint_exists(
        inspector, table_name, [id_column, "version_number"]
    )
    
    # Check indexes
    results["version_index"] = check_index_exists(
        inspector, table_name, f"idx_{table_name}_id_version"
    ) or check_index_exists(inspector, table_name, f"idx_{table_name}_version")
    results["fingerprint_index"] = check_index_exists(
        inspector, table_name, f"idx_{table_name}_fingerprint"
    )
    
    # Get row count and check for null versions
    try:
        results["row_count"] = get_row_count(session, table_name)
        null_result = session.execute(text(
            f"SELECT COUNT(*) FROM {table_name} WHERE version_number IS NULL"
        )).fetchone()
        results["null_versions"] = null_result[0] if null_result else 0
    except Exception as e:
        results["errors"].append(f"Error checking data: {e}")
    
    return results


def verify_version_table(inspector, session, table_name: str) -> dict:
    """Verify a version history table exists and has correct structure."""
    results = {
        "table": table_name,
        "exists": check_table_exists(inspector, table_name),
        "has_listing_id": False,
        "has_version_number": False,
        "has_unique_constraint": False,
        "errors": []
    }
    
    if not results["exists"]:
        results["errors"].append(f"Version table {table_name} does not exist")
        return results
    
    results["has_listing_id"] = check_column_exists(inspector, table_name, "listing_id")
    results["has_version_number"] = check_column_exists(inspector, table_name, "version_number")
    results["has_unique_constraint"] = check_composite_constraint_exists(
        inspector, table_name, ["listing_id", "version_number"]
    )
    
    return results


def print_results(results: dict, indent: int = 0):
    """Print verification results in a readable format."""
    prefix = "  " * indent
    
    for key, value in results.items():
        if key == "errors":
            if value:
                print(f"{prefix}❌ Errors:")
                for error in value:
                    print(f"{prefix}    - {error}")
        elif isinstance(value, bool):
            status = "✅" if value else "❌"
            print(f"{prefix}{status} {key}: {value}")
        elif isinstance(value, int):
            if key == "null_versions" and value > 0:
                print(f"{prefix}⚠️  {key}: {value} (should be 0)")
            else:
                print(f"{prefix}✓ {key}: {value}")
        elif isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_results(value, indent + 1)


def main():
    """Run verification."""
    print("=" * 70)
    print("🔍 Listing Versioning Migration Verification")
    print("=" * 70)
    print()
    
    try:
        # Initialize database
        config = AppConfig.from_yaml(Path(__file__).parent / "config.yaml")
        init_database(config.database)
        
        with get_session() as session:
            from src.database.connection import get_db_manager
            manager = get_db_manager()
            engine = manager._engine
            inspector = inspect(engine)
            
            all_pass = True
            
            # Verify main tables
            print("📋 Checking main tables...")
            print()
            
            tables = [
                ("listings", "listing_id"),
                ("computer_listings", "listing_id"),
                ("console_listings", "listing_id")
            ]
            
            for table, id_col in tables:
                results = verify_table(inspector, session, table, id_col)
                print(f"\n📊 {table}:")
                print_results(results, indent=1)
                
                # Check if this table passed
                if not all([
                    results["exists"],
                    results["version_column"],
                    results["fingerprint_column"],
                    results["composite_unique"],
                    results["null_versions"] == 0
                ]):
                    all_pass = False
            
            # Verify version history tables
            print("\n" + "=" * 70)
            print("📋 Checking version history tables...")
            print()
            
            version_tables = [
                "listing_versions",
                "computer_listing_versions",
                "console_listing_versions"
            ]
            
            for table in version_tables:
                results = verify_version_table(inspector, session, table)
                print(f"\n📊 {table}:")
                print_results(results, indent=1)
                
                if not all([
                    results["exists"],
                    results["has_listing_id"],
                    results["has_version_number"],
                    results["has_unique_constraint"]
                ]):
                    all_pass = False
            
            # Summary
            print("\n" + "=" * 70)
            if all_pass:
                print("✅ ALL CHECKS PASSED!")
                print("=" * 70)
                print("\n✨ Migration is complete and verified.")
                print("   You can now run scrapers with versioning support.")
                return 0
            else:
                print("❌ SOME CHECKS FAILED!")
                print("=" * 70)
                print("\n⚠️  Review the output above and fix any issues.")
                print("   Common fixes:")
                print("   - Run the SQL migration script again")
                print("   - Check PostgreSQL version (should be 11+)")
                print("   - Ensure no other processes are locking tables")
                return 1
                
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
