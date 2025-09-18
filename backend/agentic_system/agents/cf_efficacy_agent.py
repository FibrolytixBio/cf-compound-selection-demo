import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import dspy

from ..tools.chembl_tools import CHEMBL_TOOLS
from ..tools.pubchem_tools import PUBCHEM_TOOLS
from ..tools.search_tools import SEARCH_TOOLS


class EfficacyAssessment(dspy.Signature):
    """
    Estimate the efficacy of a compound for reversing the failing cardiac fibroblast phenotype using a Cell Painting + ML readout, as measured by a custom in vitro assay.
    - Assay: 10 µM compound (in DMSO) is applied to failing primary human ventricular fibroblasts in 96-well plates for 72 h alongside a DMSO-only control.
    - Readout: multiplexed Cell Painting imaging is performed; single-cell morphology features are extracted and scored by a validated classifier that distinguishes “failing” vs “nonfailing” fibroblasts.
    - Efficacy metric (0-1): predicted_efficacy = mean (P_nonfailing(cell_i | treated well)).
      • 0 -> all cells appear failing (model assigns ~0 to treated cells).
      • 1 -> all cells appear fully reverted to nonfailing (model assigns ~1 to treated cells).
    """

    compound_name: str = dspy.InputField(
        desc="Name of the compound to assess efficacy for."
    )
    predicted_efficacy: float = dspy.OutputField(
        desc="Predicted mean per-cell probability of nonfailing/quiescent-like state (0-1) in treated wells."
    )
    confidence: float = dspy.OutputField(
        desc="Confidence (0-1) based on abundance, relevance, and quality of evidence."
    )


class CFEfficacyAgent(dspy.Module):
    def __init__(self, max_iters=10):
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
