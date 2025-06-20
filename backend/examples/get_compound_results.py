from pathlib import Path
import json

from dotenv import load_dotenv
import dspy
from agentic_system.agents.compound_prioritization.compound_prioritization_agent import (
    CompoundPrioritizationAgent,
)

COMPOUND = "tanespimycin"
NUM_RESULTS = 2
SAVE_DIR = Path("compound_results/")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv("../.env")
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5))
dspy.configure_cache(
    enable_disk_cache=False,
    enable_memory_cache=False,
)

agent = CompoundPrioritizationAgent()
for i in range(NUM_RESULTS):
    result = agent.forward(compound_name=COMPOUND, hierarchical_result=True)
    result_path = SAVE_DIR / f"{COMPOUND}_result_{i}.json"

    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
