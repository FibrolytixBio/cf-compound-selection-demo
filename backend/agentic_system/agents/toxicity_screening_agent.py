import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import dspy

from ..tools.chembl_tools import CHEMBL_TOOLS
from ..tools.pubchem_tools import PUBCHEM_TOOLS
from ..tools.search_tools import SEARCH_TOOLS


class ToxicityScreening(dspy.Signature):
    """Estimate toxicity of a compound in a screening assay"""

    compound_name: str = dspy.InputField(
        desc="Name of the compound to esimate toxicity for."
    )
    percent_remaining_cells: int = dspy.OutputField(
        desc="""
        Esimate the percent of cells remaining after the compound is applied in a screening assay.
        In this screen a 10 uM solution of the compound is suspending in DMSO and applied to a well with primary human ventricular fibroblasts.
        """
    )
    confidence: float = dspy.OutputField(
        desc="""
        Confidence as probability (0-1) that predicted remaining cell count is accurate.
        Based on the availability, quality, and relevance of the data used to make the prediction.
        """
    )


class ToxicityScreeningAgent(dspy.Module):
    def __init__(self, max_iters=5):
        super().__init__()

        tools = SEARCH_TOOLS + CHEMBL_TOOLS + PUBCHEM_TOOLS

        self.agent = dspy.ReAct(
            ToxicityScreening,
            tools=tools,
            max_iters=max_iters,
        )

    def forward(self, compound_name: str):
        return self.agent(compound_name=compound_name)


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")
    dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5))

    agent = ToxicityScreeningAgent()
    result = agent.forward(compound_name="Givinostat")

    print(result)
    dspy.inspect_history(n=5)
