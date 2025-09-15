from pydantic import BaseModel, Field
import pandas as pd
import litellm
from openai import OpenAI

LITL_DATA_PATH = "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/litl_data/litl_data.csv"


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
In this screen a 10 uM solution of the compound is suspended in DMSO and applied to well with primary human ventricular fibroblasts.

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


def get_experimental_efficacy_reasoning(request: EfficacyReasoningRequest) -> str:
    """Get reasoning about a compound's efficacy in reversing cardiac fibrosis based on experimental results."""
    efficacy_df = pd.read_csv(LITL_DATA_PATH)
    efficacy_df = efficacy_df[efficacy_df.compound_name != request.compound]
    # format the reference data for the model
    ref_rows = [
        f"{row.compound_name} | {row.cf_efficacy:.2f}"
        for _, row in efficacy_df.iterrows()
    ]
    efficacy_block = "\n".join(ref_rows)

    prompt = f"""
You are an expert in cardiac fibrosis drug discovery. Below is a table showing real efficacy scores for compounds tested in a high-content screen.
In this screen a 10 uM solution of the compound is suspended in DMSO and applied to well with primary human ventricular fibroblasts.
A score of 0 indicates no efficacy (no fibroblasts reversed), while a score of 1 indicates complete efficacy (all fibroblasts reversed).

Compound | Efficacy (0–1)
{efficacy_block}

Task: For the query compound **{request.compound}**  
1. Identify any reference compounds helpful for understanding efficacy, focusing on factors like shared mechanisms, structural similarity, or prior usage in fibrosis contexts.
2. Assess the relevance of each match by comparing key factors such as:
- Target/pathway similarity
- Binding mode
- Phenotypic profile overlap
- Subcellular localization
- Cell-type specificity
- (other relevant factors)
3. Provide detailed inference/comparison notes for each relevant compound, explaining how it relates to the query compound's efficacy.

If there are no relevant compounds, simply say: “No relevant compound found in experimental data.”

Format the response as a table with columns for:
Reference Compound | Efficacy Score (0–1) | Inference and Comparison Notes


Ex:

Query Compound: Tanespimycin

| Reference Compound | Efficacy Score (0–1) | Inference and Comparison Notes |
|--------------------|----------------------|--------------------------------|
| Luminespib | 0.XX | Like Tanespimycin, it is a first-generation N-terminal Hsp90 ATP-site inhibitor. Both drugs share the same canonical binding mode in the Hsp90 pocket and drive degradation of the same client set (e.g., AKT, ERK, TGF-β pathway mediators) controlling fibroblast activation. Differences: (i) Tanespimycin requires NQO1-mediated bioactivation; Luminespib does not. (ii) Tanespimycin is a P-gp substrate with lower intracellular accumulation. (iii) Its quinone moiety may cause oxidative stress, confounding phenotype. Overall, Tanespimycin is expected to have slightly lower efficacy but still be among the top candidates due to shared mechanism. |

Only include the table in the response – no markdown, no extra commentary.
"""

    client = OpenAI()

    resp = client.responses.create(
        model="o3",
        input=prompt,
        # tools=[{"type": "web_search"}],
    )
    return resp.output[1].content[0].text


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(
        "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/.env"
    )
    efficacy_reasoning = get_experimental_efficacy_reasoning(
        request=EfficacyReasoningRequest(compound="Finasteride")
    )
    print(efficacy_reasoning)
