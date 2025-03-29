from core.workflow_manager import graph

if __name__ == "__main__":
    # Run the LangGraph once
    graph.invoke({"db_id": 123, "model": "llama3.2"})
