import modal
from pydantic import BaseModel
import dspy
from agentic_system.agents.compound_prioritization.compound_prioritization_agent import (
    CompoundPrioritizationAgent,
)

# Modal setup
image = (
    modal.Image.debian_slim()
    .run_commands("pip install uv")
    .copy_local_file("pyproject.toml", "pyproject.toml")
    .run_commands(
        [
            "uv sync",  # Install from lockfile if you have one
            "uv pip install -e .",  # Or install your package
        ]
    )
    .add_local_python_source("agentic_system")
)
app = modal.App("compound-prioritization", image=image)

# Container-level globals
_agent = None
_configured = False


class CompoundRequest(BaseModel):
    compound_name: str


class CompoundResponse(BaseModel):
    status: str
    data: dict = None
    error: str = None


def _initialize_if_needed():
    """Initialize the agent and DSPy configuration if not already done."""
    global _agent, _configured

    if not _configured:
        try:
            dspy.configure(
                lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5)
            )
            _agent = CompoundPrioritizationAgent()
            _configured = True
            print("Agent initialized successfully")
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            raise e


@app.function(
    secrets=[modal.Secret.from_name("test-secret")],
    scaledown_window=300,
    cpu=4,
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def prioritize_compound(request: CompoundRequest) -> CompoundResponse:
    """Prioritize a compound for cardiac fibrosis therapeutic development."""
    import agentic_system.tools.chembl_mcp_server

    return None
    # global _agent

    # try:
    #     # Initialize if not already done
    #     _initialize_if_needed()

    #     if _agent is None:
    #         return CompoundResponse(status="error", error="Agent initialization failed")

    #     # Process the compound
    #     result = _agent.forward(
    #         compound_name=request.compound_name,
    #         hierarchical_result=True,
    #     )

    #     return result

    # except Exception as e:
    #     print(f"Error processing compound {request.compound_name}: {e}")
    #     return CompoundResponse(status="error", error=str(e))


# For local testing
if __name__ == "__main__":
    import json

    # Test the function locally
    test_request = CompoundRequest(compound_name="Givinostat")
    response = prioritize_compound(test_request)
    print(json.dumps(response.model_dump(), indent=2))
