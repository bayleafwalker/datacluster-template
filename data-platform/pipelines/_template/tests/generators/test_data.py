"""
Test Data Generator

Generates synthetic data matching landing schema for testing.
"""
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker

fake = Faker()


class TestDataGenerator:
    """Generate realistic test data for pipeline testing"""
    
    def __init__(self, schema_path: str = None):
        """
        Initialize generator
        
        Args:
            schema_path: Path to Avro schema (optional, for validation)
        """
        self.schema_path = schema_path
        # TODO: Load and validate against schema if provided
    
    def generate_record(self) -> Dict[str, Any]:
        """Generate a single test record"""
        
        return {
            "id": fake.uuid4(),
            "timestamp": int(datetime.now().timestamp() * 1000),
            "source_system": random.choice(["system_a", "system_b", "system_c"]),
            "data": {
                "field1": fake.word(),
                "field2": fake.random_int(1, 100),
                "field3": fake.email()
            },
            "metadata": {
                "version": "v1.0",
                "ingestion_time": int(datetime.now().timestamp() * 1000)
            }
        }
    
    def generate_batch(self, num_records: int = 1000) -> List[Dict[str, Any]]:
        """
        Generate batch of test records
        
        Args:
            num_records: Number of records to generate
            
        Returns:
            List of test records
        """
        return [self.generate_record() for _ in range(num_records)]
    
    def generate_edge_cases(self) -> List[Dict[str, Any]]:
        """Generate edge case records for robustness testing"""
        
        return [
            # Null metadata
            {
                "id": fake.uuid4(),
                "timestamp": int(datetime.now().timestamp() * 1000),
                "source_system": "system_a",
                "data": {},
                "metadata": None
            },
            # Empty data
            {
                "id": fake.uuid4(),
                "timestamp": int(datetime.now().timestamp() * 1000),
                "source_system": "system_b",
                "data": {},
                "metadata": {"version": "v1.0", "ingestion_time": int(datetime.now().timestamp() * 1000)}
            },
            # Very old timestamp
            {
                "id": fake.uuid4(),
                "timestamp": int((datetime.now() - timedelta(days=365)).timestamp() * 1000),
                "source_system": "system_c",
                "data": {"field1": "old_data"},
                "metadata": {"version": "v0.9", "ingestion_time": int(datetime.now().timestamp() * 1000)}
            },
            # Future timestamp
            {
                "id": fake.uuid4(),
                "timestamp": int((datetime.now() + timedelta(days=1)).timestamp() * 1000),
                "source_system": "system_a",
                "data": {"field1": "future_data"},
                "metadata": {"version": "v1.1", "ingestion_time": int(datetime.now().timestamp() * 1000)}
            }
        ]
    
    def generate_duplicates(self, num_records: int = 100, duplicate_rate: float = 0.1) -> List[Dict[str, Any]]:
        """
        Generate dataset with intentional duplicates for dedup testing
        
        Args:
            num_records: Total number of records
            duplicate_rate: Fraction of records that are duplicates
            
        Returns:
            List with duplicates
        """
        records = []
        num_unique = int(num_records * (1 - duplicate_rate))
        
        # Generate unique records
        for _ in range(num_unique):
            records.append(self.generate_record())
        
        # Add duplicates
        num_duplicates = num_records - num_unique
        for _ in range(num_duplicates):
            # Pick random existing record and duplicate with slight variation
            base_record = random.choice(records).copy()
            base_record["timestamp"] = int(datetime.now().timestamp() * 1000)  # Same ID, different timestamp
            records.append(base_record)
        
        random.shuffle(records)
        return records
    
    def write_to_json(self, records: List[Dict[str, Any]], output_path: str):
        """Write records to JSON file"""
        with open(output_path, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        print(f"✓ Wrote {len(records)} records to {output_path}")
    
    def write_to_csv(self, records: List[Dict[str, Any]], output_path: str):
        """Write records to CSV file (flattened structure)"""
        import csv
        
        if not records:
            return
        
        # Flatten nested structures
        flattened = []
        for record in records:
            flat = {
                "id": record["id"],
                "timestamp": record["timestamp"],
                "source_system": record["source_system"],
            }
            # Flatten data dict
            if "data" in record and record["data"]:
                for k, v in record["data"].items():
                    flat[f"data_{k}"] = v
            
            flattened.append(flat)
        
        # Write CSV
        with open(output_path, 'w', newline='') as f:
            if flattened:
                writer = csv.DictWriter(f, fieldnames=flattened[0].keys())
                writer.writeheader()
                writer.writerows(flattened)
        
        print(f"✓ Wrote {len(records)} records to {output_path}")


def main():
    """CLI for generating test data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test data for pipeline")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--count", type=int, default=1000, help="Number of records")
    parser.add_argument("--edge-cases", action="store_true", help="Include edge cases")
    parser.add_argument("--duplicates", type=float, default=0.0, help="Duplicate rate (0.0-1.0)")
    
    args = parser.parse_args()
    
    generator = TestDataGenerator()
    
    # Generate records
    if args.duplicates > 0:
        records = generator.generate_duplicates(args.count, args.duplicates)
    else:
        records = generator.generate_batch(args.count)
    
    # Add edge cases if requested
    if args.edge_cases:
        records.extend(generator.generate_edge_cases())
    
    # Write output
    if args.format == "json":
        generator.write_to_json(records, args.output)
    else:
        generator.write_to_csv(records, args.output)
    
    print(f"✓ Generated {len(records)} test records")


if __name__ == "__main__":
    main()
