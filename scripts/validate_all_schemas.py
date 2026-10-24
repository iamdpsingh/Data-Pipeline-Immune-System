#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def validate_schemas():
    schema_dir = Path("schemas")
    json_files = list(schema_dir.glob("**/*.json"))
    for f in json_files:
        with open(f) as fp:
            try:
                json.load(fp)
            except Exception as e:
                print(f"Invalid JSON in {f}: {e}")
                sys.exit(1)
    print(f"Successfully validated {len(json_files)} lakehouse schema contracts.")

if __name__ == "__main__":
    validate_schemas()
