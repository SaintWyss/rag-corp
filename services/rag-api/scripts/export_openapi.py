import argparse
import json
from app.main import app

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    schema = app.openapi()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
