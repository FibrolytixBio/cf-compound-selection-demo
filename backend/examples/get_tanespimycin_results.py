from dotenv import load_dotenv
import dspy
from agentic_system.agents.compound_prioritization.compound_prioritization_agent import (
    CompoundPrioritizationAgent,
)

load_dotenv("../.env")
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5))

agent = CompoundPrioritizationAgent()
result = agent.forward(compound_name="tanespimycin", hierarchical_result=True)
print(result)
