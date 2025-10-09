import pickle

import dspy
import pandas as pd


LITL_DATA_PATH = "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/litl_data/litl_data.csv"
SUMMARIZED_TOOL_RUNS = "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/litl_data/1__no_litl_run_reflections.pkl"

with open(
    SUMMARIZED_TOOL_RUNS,
    "rb",
) as f:
    docs = pickle.load(f)


def LITL__get_all_compounds(compound_to_exclude):
    """Retrieve a dataframe of all compounds and their efficacy scores from past assay screening runs.

    Args:
        compound_to_exclude (str): The name of the compound being investigated (should be excluded from the results).

    Returns:
        pd.DataFrame: A dataframe with columns 'compound' and 'efficacy_score', sorted by efficacy_score descending.
    """

    efficacy_df = pd.read_csv(LITL_DATA_PATH)
    efficacy_df = efficacy_df[
        efficacy_df.compound_name.str.lower() != compound_to_exclude.lower()
    ]
    # format the reference data for the model
    ref_rows = [
        f"{row.compound_name} | {row.cf_efficacy:.2f}"
        for _, row in efficacy_df.iterrows()
    ]
    efficacy_block = "\n".join(ref_rows)

    return "Compound | Real Efficacy (0-1)\n" + efficacy_block


def LITL__efficacy_reasoning(compound: str) -> str:
    """Get inference/comparison notes about screened compound efficacies for reversing cardiac fibrosis based on assay results.

    Args:
        compound (str): The name of the compound being evaluated for similar compounds.

    Returns:
        str: A table with columns for Reference Compound, Efficacy Score (0-1), and Inference/Comparison Notes
    """
    efficacy_df = pd.read_csv(LITL_DATA_PATH)
    efficacy_df = efficacy_df[efficacy_df.compound_name.str.lower() != compound.lower()]
    # format the reference data for the model
    ref_rows = [
        f"{row.compound_name} | {row.cf_efficacy:.2f}"
        for _, row in efficacy_df.iterrows()
    ]
    efficacy_block = "\n".join(ref_rows)

    class EfficacyReasoning(dspy.Signature):
        """You are an expert in cardiac fibrosis drug discovery. Below is a table showing real efficacy scores for compounds tested in a high-content screen.
        In this screen a 10 uM solution of the compound is suspended in DMSO and applied to well with primary human ventricular fibroblasts.
        A score of 0 indicates no efficacy (no fibroblasts reversed), while a score of 1 indicates complete efficacy (all fibroblasts reversed).

        Task: For the query compound **{compound}**
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
        Reference Compound | Efficacy Score (0-1) | Inference and Comparison Notes


        Ex:

        Query Compound: Tanespimycin

        | Reference Compound | Efficacy Score (0-1) | Inference and Comparison Notes |
        |--------------------|----------------------|--------------------------------|
        | Luminespib | 0.XX | Like Tanespimycin, it is a first-generation N-terminal Hsp90 ATP-site inhibitor. Both drugs share the same canonical binding mode in the Hsp90 pocket and drive degradation of the same client set (e.g., AKT, ERK, TGF-β pathway mediators) controlling fibroblast activation. Differences: (i) Tanespimycin requires NQO1-mediated bioactivation; Luminespib does not. (ii) Tanespimycin is a P-gp substrate with lower intracellular accumulation. (iii) Its quinone moiety may cause oxidative stress, confounding phenotype. Overall, Tanespimycin is expected to have slightly lower efficacy but still be among the top candidates due to shared mechanism. |

        Only include the table in the response – no markdown, no extra commentary.
        """

        efficacy_block: str = dspy.InputField(
            desc="The efficacy block including compounds and their efficacy scores for comparison"
        )
        compound_name: str = dspy.InputField(
            desc="The name of the compound being evaluated"
        )
        reasoning_table: str = dspy.OutputField(
            desc="A table with columns for Reference Compound, Efficacy Score (0-1), and Inference/Comparison Notes"
        )

    reasoning_lm = dspy.LM(
        "gemini/gemini-2.5-pro", temperature=0.0, cache=True, max_tokens=10000
    )

    with dspy.context(lm=reasoning_lm):
        efficacy_reasoning_predict = dspy.ChainOfThought(EfficacyReasoning)
        efficacy_reasoning_result = efficacy_reasoning_predict(
            efficacy_block=efficacy_block,
            compound_name=compound,
        )
        return efficacy_reasoning_result.reasoning_table


def LITL__rag_query(query, compound_to_exclude):
    """
    Query previous agent runs for insights into compound efficacy in reversing cardiac fibrosis.

    This function retrieves and summarizes information from past agent executions that evaluated
    similar compounds, including what worked well, what went wrong, and suggestions for improvement.

    Args:
        query (str): A natural language query to investigate past agent runs.
        compound_to_exclude (str): The name of the compound being investigated (should be excluded from the results).

    Returns:
        str: A response based on relevant previous runs, including trajectory summaries, reasoning, predictions, and reflections on accuracy.
    """

    filtered_docs = [
        doc for doc in docs if not compound_in_doc(compound_to_exclude, doc)
    ]

    NUM_DOCS = 5
    embedder = dspy.Embedder(
        "gemini/text-embedding-004", dimensions=768, batch_size=100
    )
    search = dspy.retrievers.Embeddings(
        embedder=embedder, corpus=filtered_docs, k=NUM_DOCS
    )  # FAISS auto-handled if installed

    class MemoryRAG(dspy.Signature):
        """Create a concise answer to the query based on relevant past agent runs."""

        context: str = dspy.InputField(
            desc="Previous agent run summaries relevant to the query"
        )
        query: str = dspy.InputField(desc="The query to answer")
        summary: str = dspy.OutputField(
            desc="A summary of the findings from relevant past agent runs"
        )

    memory_rag_lm = dspy.LM(
        "gemini/gemini-2.5-pro", temperature=0.0, cache=True, max_tokens=10000
    )

    with dspy.context(lm=memory_rag_lm):
        ctx = search(query).passages
        numbered_ctx = [f"Context {i + 1}:\n{passage}" for i, passage in enumerate(ctx)]

        memory_rag_predict = dspy.Predict(MemoryRAG)
        memory_rag_result = memory_rag_predict(
            context="\n\n".join(numbered_ctx),
            query=query,
        )
        return memory_rag_result.summary


def LITL__get_runs(reference_compound, n_runs=1):
    """Retrieve past agent runs for a specific compound. Useful for understanding agent runs logic/accuracy for a compound.
    DO NOT USE FOR COMPOUND BEING EVALUATED. ONLY USE TO SEARCH FOR PAST RUNS OF OTHER COMPOUNDS.

    Args:
        reference_compound (str): The name of the compound to retrieve runs for. CANNOT BE THE COMPOUND WE ARE PREDICTING EFFICACY FOR.
        n_runs (int, optional): The number of runs to retrieve. Defaults to 1.

    Returns:
        list: A list of strings, each representing a past agent run related to the specified compound
    """

    compound_docs = []
    for doc in docs:
        if compound_in_doc(reference_compound, doc):
            compound_docs.append(doc)

    if len(compound_docs) == 0:
        return ["No past runs found for this compound."]

    return compound_docs[:n_runs]


def compound_in_doc(compound, doc):
    return f"## Compound\n{compound}".lower() in doc.lower()


LITL_TOOLS = [
    LITL__rag_query,
    LITL__get_runs,
    LITL__get_all_compounds,
    LITL__efficacy_reasoning,
]

if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")

    # result = LITL__efficacy_reasoning("Tanespimycin")
    # print(result)

    # result = LITL__get_runs("Anastrozole")
    # print(result)

    compounds = set()
    for doc in docs:
        start = doc.find("## Compound\n")
        if start != -1:
            compound = doc[start + len("## Compound\n") :].split("\n")[0].strip()
            compounds.add(compound)
    print("All compounds:")
    print(len(sorted(compounds)))
    for c in sorted(compounds):
        print(c)
