from dotenv import load_dotenv
import dspy

from agentic_system.agents import CFEfficacyAgent

load_dotenv("../.env")
dspy.configure(
    lm=dspy.LM(
        "gemini/gemini-2.5-flash-lite", temperature=0.5, cache=True, rollout_id=1
    )
)

agent = CFEfficacyAgent(max_iters=3)

COMPOUND = "Luminespib"
