from dotenv import load_dotenv
import dspy
from agentic_system.agents.compound_prioritization.compound_prioritization_agent import (
    CompoundPrioritizationAgent,
)

COMPOUND = "Anastrozole"

load_dotenv("../.env")
dspy.configure(
    lm=dspy.LM(
        "gemini/gemini-2.5-flash-preview-05-20",
        temperature=0.8,
    )
)

agent = CompoundPrioritizationAgent()
result = agent.forward(compound_name=COMPOUND, hierarchical_result=True)
print(result)
