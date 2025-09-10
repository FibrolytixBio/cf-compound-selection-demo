import dspy

from ....tools.chembl_tools import CHEMBL_TOOLS
from ....tools.pubchem_tools import PUBCHEM_TOOLS
from ....tools.search_tools import SEARCH_TOOLS


class EfficacyAssessment(dspy.Signature):
    """Estimate efficacy of a compound for reversing cardiac fibrosis in a screening assay

    Always use the `get_experimental_efficacy_reasoning` tool first (if it exists) to understand if there are relevant experimental results for the compound.
    Always perform a search for existing preclinical data on the compound in a cardiac fibrosis context and give this evidence the highest priority when predicting efficacy.
    """

    compound_name: str = dspy.InputField(
        desc="Name of the compound to assess efficacy for."
    )
    predicted_efficacy: float = dspy.OutputField(
        desc="""
        Esimate the compound efficacy (0-1) for reversing cardiac fibrosis in a screening assay.
        In this screen a 10 uM solution of the compound is suspending in DMSO and applied to a well with primary human ventricular fibroblasts.
        A score of 0 indicates no efficacy (no fibroblasts reversed), while a score of 1 indicates complete efficacy (all fibroblasts reversed).
        """
    )
    confidence: float = dspy.OutputField(
        desc="""
        Confidence as probability (0-1) that predicted remaining cell count is accurate.
        Based on the availability, quality, and relevance of the data used to make the prediction.
        """
    )


class CFEfficacyAgent(dspy.Module):
    def __init__(self, max_iters=5):
        super().__init__()

        tools = SEARCH_TOOLS + CHEMBL_TOOLS + PUBCHEM_TOOLS

        self.agent = dspy.ReAct(
            EfficacyAssessment,
            tools=tools,
            max_iters=max_iters,
        )

    def forward(self, compound_name):
        return self.agent(compound_name=compound_name)


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")

    dspy.configure(lm=dspy.LM("gemini/gemini-2.5-pro", temperature=0.5, cache=False))

    agent = CFEfficacyAgent()
    result = agent.forward(compound_name="Givinostat")
    print(result)

    dspy.inspect_history(n=5)
