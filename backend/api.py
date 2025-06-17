import logging


from pydantic import BaseModel
from dotenv import load_dotenv
import dspy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from drug_fibrosis_agent.coordinator import evaluate_drug
from agentic_system.agents.compound_prioritization.compound_prioritization_agent import (
    CompoundPrioritizationAgent,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from current directory
load_dotenv(".env")

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware with more specific configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://birdhouse-omega.vercel.app",
        "https://cf-compound-selection.vercel.app",
    ],  # Frontend URL
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],  # Explicitly list allowed methods
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


class CompoundPrioritizationRequest(BaseModel):
    compound_name: str


@app.post("/prioritize_compound")
def get_compound_prioritization(request: CompoundPrioritizationRequest):
    dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5))

    compoundPriortizationAgent = CompoundPrioritizationAgent()
    result = compoundPriortizationAgent(
        compound_name=request.compound_name, hierarchical_result=True
    )
    logger.info(
        f"Compound prioritization result for {request.compound_name}:\n{result}"
    )

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
