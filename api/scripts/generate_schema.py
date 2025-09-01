#!/usr/bin/env python3
"""Generate OpenAPI schema from FastAPI app and save to contract directory."""

import json
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import the app
sys.path.append(str(Path(__file__).parent.parent))

from app.main import app


def main():
    """Generate and save OpenAPI schema."""
    # Get the OpenAPI schema from FastAPI
    openapi_schema = app.openapi()

    # Path to save the schema (relative to api directory)
    contract_dir = Path(__file__).parent.parent.parent / "contract"
    contract_dir.mkdir(exist_ok=True)

    schema_path = contract_dir / "openapi.json"

    # Save the schema
    with open(schema_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema generated and saved to {schema_path}")


if __name__ == "__main__":
    main()
