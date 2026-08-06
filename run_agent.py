# path: run_agent.py
"""Entry point: Runtime + HTTP ingestion (pattern call-and-drain)."""
import os
import signal

import uvicorn
from dotenv import load_dotenv

from activegraph import Runtime, Graph
from activegraph.llm import AnthropicProvider

from k8s_sentinel.pack import k8s_sentinel_pack
from k8s_sentinel.ingestion import GoalListener

# Carica .env PRIMA di leggere le variabili e prima che i behavior leggano env
load_dotenv()


def _stop(*_args):
    raise SystemExit(0)


def main():
    rt = Runtime(
        Graph(),
        llm_provider=AnthropicProvider(),
        persist_to=os.getenv("ACTIVEGRAPH_PERSIST_TO", "sqlite:///data/sentinel.db"),
    )
    # Il run_id è generato dal framework e accessibile come rt.run_id
    rt.load_pack(k8s_sentinel_pack)

    listener = GoalListener(rt)
    host = os.getenv("INGESTION_HOST", "0.0.0.0")
    port = int(os.getenv("INGESTION_PORT", "9000"))

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    print(f"K8s Sentinel started: run_id={rt.run_id}")
    print(f"HTTP server listening on {host}:{port}")

    uvicorn.run(listener.app, host=host, port=port)


if __name__ == "__main__":
    main()
