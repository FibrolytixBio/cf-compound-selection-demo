from pathlib import Path

import dspy

from ....tools.tool_utils import get_mcp_tools

from ....tools.search import search_web, search_pubmed_abstracts
from ....tools.litl_tools import get_experimental_efficacy_reasoning

TOOLS = [search_web, search_pubmed_abstracts, get_experimental_efficacy_reasoning]

from ....tools import chembl_mcp_server
from ....tools import pubchem_mcp_server

MCP_SERVER_PATHS = [
    Path(chembl_mcp_server.__file__).resolve(),
    Path(pubchem_mcp_server.__file__).resolve(),
]


class EfficacyAssessment(dspy.Signature):
    """Estimate efficacy of a compound for reversing cardiac fibrosis in a screening assay

    Always use the `get_experimental_efficacy_reasoning` tool first to understand if there are relevant experimental results for the compound,
    but prioritize existing experimental data for this particular compound in other cardiac fibrosis assay sources.
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

        tools = []
        for mcp_server in MCP_SERVER_PATHS:
            tools.extend(get_mcp_tools(mcp_server))
        for tool in TOOLS:
            tools.append(tool)

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

    dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5))

    agent = CFEfficacyAgent()
    result = agent.forward(compound_name="Givinostat")
    print(result)

    dspy.inspect_history(n=5)
