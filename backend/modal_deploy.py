import modal
from pydantic import BaseModel
import dspy

# Modal setup
image = (
    modal.Image.debian_slim()
    .pip_install_from_pyproject("pyproject.toml")
    .add_local_python_source("agentic_system")
)

app = modal.App("compound-prioritization", image=image)

# Container-level globals
_agent = None


class CompoundRequest(BaseModel):
    compound_name: str


def _initialize_if_needed():
    """Initialize the agent and DSPy configuration if not already done."""
    global _agent

    if _agent is None:
        from agentic_system.agents.compound_prioritization.compound_prioritization_agent import (
            CompoundPrioritizationAgent,
        )

        dspy.configure(
            lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5)
        )
        _agent = CompoundPrioritizationAgent()
        print("Agent initialized successfully")


@app.function(
    secrets=[modal.Secret.from_name("test-secret")],
    scaledown_window=120,
    cpu=1,
    memory=512,
)
@modal.fastapi_endpoint(method="POST")
def prioritize_compound(request: CompoundRequest):
    """Prioritize a compound for cardiac fibrosis therapeutic development."""

    _initialize_if_needed()

    # Process the compound
    result = _agent(
        compound_name=request.compound_name,
        hierarchical_result=True,
    )

    return result
