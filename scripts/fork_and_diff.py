# path: scripts/fork_and_diff.py
"""Fork a run at an event and print the diff command."""
import argparse
from activegraph.store.sqlite import SQLiteEventStore

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--store", required=True)
    p.add_argument("--parent-run", required=True)
    p.add_argument("--at-event", required=True)
    p.add_argument("--fork-run", required=True)
    a = p.parse_args()
    SQLiteEventStore.fork_run(a.store.replace("sqlite:///", ""),
        parent_run_id=a.parent_run, new_run_id=a.fork_run,
        at_event_id=a.at_event, label="experiment")
    print(f"activegraph diff {a.store} --run-a {a.parent_run} --run-b {a.fork_run}")

if __name__ == "__main__":
    main()
