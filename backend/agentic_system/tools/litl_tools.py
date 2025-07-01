from pydantic import BaseModel, Field
import pandas as pd
import litellm

LITL_DATA_PATH = "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/tools/litl_data.csv"


class LITLPCRReasoningRequest(BaseModel):
    compound: str = Field(
        description="Name of the compound to evaluate using lab-in-the-loop (LITL) data."
    )


def get_litl_pcr_reasoning(request: LITLPCRReasoningRequest) -> str:
    """Get reasoning about a compound's percent cells remaining directly from experimental results. Always use this first to understand if there is existing experimental data to ground the prediction."""
    litl_df = pd.read_csv(LITL_DATA_PATH)
    # format the reference data for the model
    ref_rows = [
        f"{row.compound_name} | {row.percent_remaining_cells:.2f}%"
        for _, row in litl_df.iterrows()
    ]
    litl_block = "\n".join(ref_rows)

    prompt = f"""
You are a medicinal-chemistry expert helping an AI toxicity-screening agent determine percent-cells-remaining (PCR) for a compound in a screen.
In this screen a 10 uM solution of the compound is suspending in DMSO and applied to well with primary human ventricular fibroblasts.

Below is experimental percent-cells-remaining (PCR) data from the same assay:

Compound | PCR (%)  
{litl_block}

Task: For the query compound **{request.compound}**  
1. Identify any compounds in the table with a close mechanistic match (same target, target family, or well-known off-target that dominates toxicity).  
2. Determine the relevance of the match with respect to the toxicity screen. What is similar or different between the reference and query compounds for factors like binding mode, intracellular exposure, and cell-type dependence?
3. Explain the inference in 3-4 concise sentences. If no relevant compound exists in the assay data, simply say "No relevant compound found in assay data.".

Return only the reasoning string – no markdown, no extra commentary.
"""

    response = litellm.completion(
        model="o3",
        messages=[{"role": "user", "content": prompt}],
    )
    return response["choices"][0]["message"]["content"]


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(
        "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/.env"
    )
    pcr_reasoning = get_litl_pcr_reasoning(compound="Tanespimycin")
    print(pcr_reasoning)
