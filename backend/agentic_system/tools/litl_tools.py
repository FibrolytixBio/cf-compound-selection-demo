from pydantic import BaseModel, Field
import pandas as pd
import litellm

LITL_DATA_PATH = "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/tools/litl_data.csv"


class LITLPCRReasoningRequest(BaseModel):
    compound: str = Field(
        description="Name of the compound to evaluate using lab-in-the-loop (LITL) data."
    )


def get_litl_pcr_reasoning(request: LITLPCRReasoningRequest) -> str:
    """Get reasoning about a compound's percent cells remaining directly from experimental results. ALWAYS USE THIS TOOL FIRST TO UNDERSTAND IF THERE ARE RELEVANT EXPERIMENTAL RESULTS FOR THE COMPOUND."""
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
1. Identify any reference compounds with similar mechanisms or molecular features.
2. Determine the relevance of the match, ex what is similar or different between the reference and query compounds for factors like binding mode, intracellular exposure, and cell-type dependence, etc?
3. Explain the inference in 3-4 concise sentences. If no relevant compound exists in the prediction table, say: "No relevant compound found in prediction data."

Return only the reasoning string – no markdown, no extra commentary.
"""

    response = litellm.completion(
        model="o3",
        messages=[{"role": "user", "content": prompt}],
    )
    return response["choices"][0]["message"]["content"]


class EfficacyReasoningRequest(BaseModel):
    compound: str = Field(
        description="Name of the compound to evaluate for reversing cardiac fibrosis using predicted efficacy scores."
    )


def get_predicted_efficacy_reasoning(request: EfficacyReasoningRequest) -> str:
    """Get reasoning about a compound's efficacy in reversing cardiac fibrosis based on experimental results. ALWAYS USE THIS TOOL FIRST TO UNDERSTAND IF THERE ARE RELEVANT EXPERIMENTAL RESULTS FOR THE COMPOUND."""
    efficacy_df = pd.read_csv(LITL_DATA_PATH)  # assumed to be defined
    # format the reference data for the model
    ref_rows = [
        f"Compound Name: {row.compound_name} | Efficacy: {row.predicted_efficacy:.2f}"
        for _, row in efficacy_df.iterrows()
    ]
    efficacy_block = "\n".join(ref_rows)

    prompt = f"""
You are an expert in cardiac fibrosis drug discovery. Below is a table showing real efficacy scores for compounds tested in a high-content screen. The assay measures reversal of fibrosis in human cardiac fibroblasts, where 0 is no efficacy and 1 is complete efficacy for reversing fibrosis.

Compound | Efficacy (0–1), Confidence (0–1)  
{efficacy_block}

Task: For the query compound **{request.compound}**  
1. Identify any reference compounds helpful for understanding efficacy with factors like similar mechanisms, molecular features, etc.
2. Determine the relevance of the match, ex what is similar or different between the reference and query compounds for factors like binding mode, intracellular exposure, and cell-type dependence, etc?
3. Explain the inference in 3-4 concise sentences. If no relevant compound exists in the prediction table, say: "No relevant compound found in prediction data."

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
    efficacy_reasoning = get_predicted_efficacy_reasoning(
        request=EfficacyReasoningRequest(compound="Tanespimycin")
    )
    print(efficacy_reasoning)
