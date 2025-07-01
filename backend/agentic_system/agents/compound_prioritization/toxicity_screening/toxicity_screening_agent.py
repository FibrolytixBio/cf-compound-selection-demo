from pathlib import Path

import dspy


from ....tools.tool_utils import get_mcp_tools

from ....tools.search import search_web, search_pubmed_abstracts

TOOLS = [search_web, search_pubmed_abstracts]

from ....tools import chembl_mcp_server
from ....tools import pubchem_mcp_server

MCP_SERVER_PATHS = [
    Path(chembl_mcp_server.__file__).resolve(),
    Path(pubchem_mcp_server.__file__).resolve(),
]


class ToxicityScreening(dspy.Signature):
    """Estimate toxicity of a compound in a screening assay"""

    compound_name: str = dspy.InputField(
        desc="Name of the compound to esimate toxicity for."
    )
    percent_remaining_cells: int = dspy.OutputField(
        desc="""
        Esimate the percent of cells remaining after the compound is applied in a screening assay.
        In this screen a 10 uM solution of the compound is suspending in DMSO and applied to well with primary human ventricular fibroblasts.
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

        tools = []
        for mcp_server in MCP_SERVER_PATHS:
            tools.extend(get_mcp_tools(mcp_server))
        for tool in TOOLS:
            tools.append(tool)

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

    all_tools = get_mcp_tools(MCP_SERVER_PATHS[0])
    agent = ToxicityScreeningAgent()
    result = agent.forward(compound_name="Givinostat")

    print(result)
    dspy.inspect_history(n=5)
