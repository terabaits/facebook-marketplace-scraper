#!/usr/bin/env python3
"""Add Intel Core i7-10700 CPU to database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text


def add_i7_10700():
    """Add Intel Core i7-10700 CPU."""
    print("Adding Intel Core i7-10700...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    cpu_data = {
        "producer": "Intel",
        "cpu_name": "Core i7-10700",
        "processor_number": "i7-10700",
        "brand_modifier": "Core i7",
        "generation": "10",
        "cores": 8,
        "threads": 16,
        "socket": "LGA1200",
        "tdp_w": 65,
        "price": 280.0
    }
    
    with get_session() as session:
        # Check if exists
        result = session.execute(
            text("SELECT id FROM cpu_reference WHERE processor_number = :proc"),
            {"proc": cpu_data["processor_number"]}
        ).fetchone()
        
        if result:
            print(f"  Already exists: {cpu_data['processor_number']} (ID: {result[0]})")
            return
        
        # Get max ID
        max_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM cpu_reference")).scalar()
        new_id = max_id + 1
        
        # Generate keywords
        keywords = [
            cpu_data["producer"].lower(),
            cpu_data["processor_number"].lower(),
            cpu_data["cpu_name"].lower().replace(" ", ""),
            "i7",
            "10700",
            "intel i7",
            cpu_data["socket"].lower(),
        ]
        
        session.execute(
            text("""
                INSERT INTO cpu_reference 
                (id, producer, cpu_name, processor_number, brand_modifier, generation,
                 cores, threads, socket, tdp_w, price, search_keywords, normalized_name)
                VALUES (:id, :producer, :cpu_name, :processor_number, :brand_modifier, 
                        :generation, :cores, :threads, :socket, :tdp_w, :price,
                        :keywords, :normalized)
            """),
            {
                "id": new_id,
                "producer": cpu_data["producer"],
                "cpu_name": cpu_data["cpu_name"],
                "processor_number": cpu_data["processor_number"],
                "brand_modifier": cpu_data["brand_modifier"],
                "generation": cpu_data["generation"],
                "cores": cpu_data["cores"],
                "threads": cpu_data["threads"],
                "socket": cpu_data["socket"],
                "tdp_w": cpu_data["tdp_w"],
                "price": cpu_data["price"],
                "keywords": keywords,
                "normalized": normalize_text(cpu_data["cpu_name"])
            }
        )
        session.commit()
        print(f"  [OK] Added {cpu_data['cpu_name']} (ID: {new_id})")


if __name__ == "__main__":
    add_i7_10700()
