from dotenv import load_dotenv
import dspy
import mlflow

from agentic_system.agents.compound_prioritization.cf_efficacy.cf_efficacy_agent import (
    CFEfficacyAgent,
)

# NOTE: Start MLflow server with:
# mlflow server --backend-store-uri sqlite:///mydb.sqlite
# Tell MLflow about the server URI.
mlflow.set_tracking_uri("http://127.0.0.1:5000")
# Create a unique name for your experiment.
mlflow.set_experiment("DSPy")
mlflow.autolog()

load_dotenv("../.env")
dspy.configure(
    lm=dspy.LM(
        "gemini/gemini-2.5-flash-lite", temperature=0.5, cache=False, rollout_id=1
    )
)

COMPOUND = "Luminespib"

agent = CFEfficacyAgent(max_iters=12)
result = agent(compound_name=COMPOUND)
print(result)
