from dotenv import load_dotenv
import dspy
import mlflow

from agentic_system.agents import CFEfficacyAgent

# NOTE: Start MLflow server with:
# mlflow server --backend-store-uri sqlite:///mydb.sqlite
# Tell MLflow about the server URI.
mlflow.set_tracking_uri("http://127.0.0.1:5000")
# Create a unique name for your experiment.
mlflow.set_experiment("Test LITL Tools")
mlflow.autolog()
mlflow.tracing.disable_notebook_display()

load_dotenv("../.env")
# lm = dspy.LM("gemini/gemini-2.5-pro", temperature=0.9, cache=False, max_tokens=80000)
lm = dspy.LM(
    "xai/grok-4-fast-reasoning", temperature=0.8, cache=False, max_tokens=80000
)
dspy.settings.configure(lm=lm, track_usage=True)

COMPOUND = "SU11274"

efficacy_agent = CFEfficacyAgent()
efficacy_results = efficacy_agent(compound_name=COMPOUND)
print(efficacy_results)

steps = len(efficacy_results.trajectory) // 4
cost = sum([x["cost"] for x in lm.history])

print("Steps:", steps)
print("Total Cost (USD):", cost)
