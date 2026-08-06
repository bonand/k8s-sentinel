# path: scripts/improve_prompt.py
"""Fork a run at the investigation point and re-run it with the currently
installed pack (e.g. after editing k8s_sentinel/prompts.py)."""
import argparse
from activegraph import Runtime
from activegraph.llm import AnthropicProvider
from activegraph.store.sqlite import SQLiteEventStore
from k8s_sentinel.pack import k8s_sentinel_pack


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--store", required=True)
    p.add_argument("--parent-run", required=True)
    p.add_argument("--at-event", default=None,
                   help="default: first evidence.collected of the parent run")
    p.add_argument("--fork-run", required=True)
    a = p.parse_args()
    db = a.store.replace("sqlite:///", "")

    if a.at_event is None:
        parent = Runtime.load(a.store, run_id=a.parent_run)
        a.at_event = next(e.id for e in parent.graph.events
                          if e.type == "evidence.collected")

    SQLiteEventStore.fork_run(
        db, parent_run_id=a.parent_run, new_run_id=a.fork_run,
        at_event_id=a.at_event, label="prompt-experiment")

    # I behavior (e il prompt) vengono dalla working tree corrente:
    # con `pip install -e .` basta aver modificato prompts.py.
    rt = Runtime.load(a.store, run_id=a.fork_run, llm_provider=AnthropicProvider())
    rt.load_pack(k8s_sentinel_pack)
    rt.run_until_idle()
    rt.save_state()

    print(f"Done. Compare with:\n"
          f"  activegraph diff {a.store} --run-a {a.parent_run} --run-b {a.fork_run}")


if __name__ == "__main__":
    main()
