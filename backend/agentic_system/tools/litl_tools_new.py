import pickle

import dspy
import pandas as pd


LITL_DATA_PATH = "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/litl_data/litl_data.csv"

with open(
    "/Users/roshankern/Desktop/Github/cf-compound-selection-demo/backend/agentic_system/litl_data/summarized_tool_run_docs.pkl",
    "rb",
) as f:
    docs = pickle.load(f)


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
        doc for doc in docs if compound_to_exclude.lower() not in doc.lower()
    ]

    NUM_DOCS = 3
    embedder = dspy.Embedder(
        "gemini/text-embedding-004", dimensions=768, batch_size=100
    )
    search = dspy.retrievers.Embeddings(
        embedder=embedder, corpus=filtered_docs, k=NUM_DOCS
    )  # FAISS auto-handled if installed

    psg = search(query).passages
    numbered_psg = [f"Run {i + 1}:\n{passage}" for i, passage in enumerate(psg)]
    return "\n\n".join(numbered_psg)

    class MemoryRAG(dspy.Module):
        def __init__(self):
            self.respond = dspy.Predict("context, query -> answer: str")

        def forward(self, query):
            ctx = search(query).passages
            numbered_ctx = [
                f"Context {i + 1}:\n{passage}" for i, passage in enumerate(ctx)
            ]
            return self.respond(context="\n\n".join(numbered_ctx), query=query)

    rag = MemoryRAG()

    return rag(query=query).answer


def LITL__get_runs(compound, n_runs=1):
    """Retrieve past agent runs for a specific compound. Useful for understanding agent runs logic/accuracy for a compound.
    DO NOT USE FOR COMPOUND BEING EVALUATED. ONLY USE TO SEARCH FOR PAST RUNS OF OTHER COMPOUNDS.

    Args:
        compound (str): The name of the compound to retrieve runs for.
        n_runs (int, optional): The number of runs to retrieve. Defaults to 1.

    Returns:
        list: A list of strings, each representing a past agent run related to the specified compound
    """

    compound_docs = []
    for doc in docs:
        if compound.lower() in doc.lower():
            compound_docs.append(doc)

    return compound_docs[:n_runs]


def LITL__get_compounds(compound_to_exclude):
    """Retrieve a dataframe of compounds and their efficacy scores from past assay screening runs.

    Args:
        compound_to_exclude (str): The name of the compound being investigated (should be excluded from the results).

    Returns:
        pd.DataFrame: A dataframe with columns 'compound' and 'efficacy_score', sorted by efficacy_score descending.
    """

    efficacy_df = pd.read_csv(LITL_DATA_PATH)
    efficacy_df = efficacy_df[efficacy_df.compound_name != compound_to_exclude]
    # format the reference data for the model
    ref_rows = [
        f"{row.compound_name} | {row.cf_efficacy:.2f}"
        for _, row in efficacy_df.iterrows()
    ]
    efficacy_block = "\n".join(ref_rows)

    return "Compound | Real Efficacy (0–1)\n" + efficacy_block


LITL_TOOLS = [LITL__rag_query, LITL__get_runs, LITL__get_compounds]
