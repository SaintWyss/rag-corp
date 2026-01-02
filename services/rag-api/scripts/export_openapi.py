"""
Name: OpenAPI Schema Exporter

Responsibilities:
  - Generate openapi.json file from FastAPI app
  - Serialize schema with readable format (indent=2, UTF-8)

Collaborators:
  - app.main.app: FastAPI instance with defined endpoints
  - argparse: CLI argument parsing

Constraints:
  - Must run after app is fully configured
  - Doesn't validate schema against OpenAPI 3.0 spec

Notes:
  - Used by command: pnpm contracts:export
  - Output to packages/contracts/openapi.json
  - Orval consumes this file to generate TypeScript client
"""
import argparse
import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.main import app

def main():
    """
    R: CLI entrypoint to export OpenAPI schema.
    
    Usage:
        python scripts/export_openapi.py --out openapi.json
    """
    # R: Parse command line arguments
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, help="Output file path for OpenAPI schema")
    args = p.parse_args()

    # R: Generate OpenAPI schema from FastAPI app
    schema = app.openapi()
    
    # R: Write schema to file with readable formatting
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
