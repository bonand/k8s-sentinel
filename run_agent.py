# path: run_agent.py
"""Entry point: Runtime + HTTP ingestion (call-and-drain)."""
import os, signal
import uvicorn
from dotenv import load_dotenv
from activegraph import Runtime, Graph
from activegraph.llm import AnthropicProvider
from k8s_sentinel.pack import k8s_sentinel_pack
from k8s_sentinel.ingestion import GoalListener

load_dotenv()

def main():
    rt = Runtime(Graph(), llm_provider=AnthropicProvider(),
                 persist_to=os.getenv("ACTIVEGRAPH_PERSIST_TO", "sqlite:///data/sentinel.db"))
    rt.load_pack(k8s_sentinel_pack)
    listener = GoalListener(rt)
    host = os.getenv("INGESTION_HOST", "0.0.0.0")
    port = int(os.getenv("INGESTION_PORT", "9000"))
    signal.signal(signal.SIGTERM, lambda *a: (_ for _ in ()).throw(SystemExit(0)))
    uvicorn.run(listener.app, host=host, port=port)

if __name__ == "__main__":
    main()
