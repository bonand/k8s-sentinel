# path: scripts/improve_prompt.py
"""Fork at evidence.collected and re-run with a new prompt."""
import argparse
from pathlib import Path
from activegraph.store.sqlite import SQLiteEventStore

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--store", required=True)
    p.add_argument("--parent-run", required=True)
    p.add_argument("--prompt-file", required=True, type=Path)
    a = p.parse_args()
    a.prompt_file.read_text()  # il nuovo prompt va passato al pack al load
    print("Fork manually with activegraph fork, then load pack with new prompt.")

if __name__ == "__main__":
    main()
