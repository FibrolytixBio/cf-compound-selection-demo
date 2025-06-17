import logging
import os


from pydantic import BaseModel
from dotenv import find_dotenv, load_dotenv
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
dotenv_path = find_dotenv(".env")
if dotenv_path:
    load_dotenv(".env")
else:
    logger.warning("No .env file found. Environment variables may not be set.")

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware with more specific configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["https://nextjs-frontend.onrender.com"] for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
