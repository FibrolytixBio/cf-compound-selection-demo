import dspy
from agentic_system.agents.compound_prioritization.cf_efficacy.cf_efficacy_agent import (
    CFEfficacyAgent,
)
from agentic_system.agents.compound_prioritization.toxicity_screening.toxicity_screening_agent import (
    ScreeningToxicityAgent,
)


class CompoundPrioritization(dspy.Signature):
    """Prioritize compounds for cardiac fibrosis therapeutic development."""

    efficacy_assessment = dspy.InputField(desc="Efficacy assessment results")
    toxicity_assessment = dspy.InputField(desc="Toxicity screening results")

    priority_score: float = dspy.OutputField(
        desc="Overall priority score (0-1). Higher means higher priority"
    )
    confidence: float = dspy.OutputField(
        desc="""
        Confidence as probability (0-1) that predicted remaining cell count is accurate.
        Based on the availability, quality, and relevance of the data used to make the prediction.
        """
    )


class CompoundPrioritizationAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        # Sub-agents
        self.efficacy_agent = CFEfficacyAgent()
        self.toxicity_agent = ScreeningToxicityAgent()

        # Coordination predictor
        self.coordinator = dspy.ChainOfThought(CompoundPrioritization)

    def forward(self, compound_name, hierarchical_result=False):
        # Run sub-agents
        efficacy_result = self.efficacy_agent(compound_name=compound_name)
        toxicity_result = self.toxicity_agent(compound_name=compound_name)

        # Get prioritization results
        result = self.coordinator(
            efficacy_assessment=f"""
                Efficacy Score: {efficacy_result.predicted_efficacy},
                Confidence: {efficacy_result.confidence},
                Reasoning: {efficacy_result.reasoning}
                """,
            toxicity_assessment=f"""
                Percent Remaining Cells: {toxicity_result.percent_remaining_cells},
                Confidence: {toxicity_result.confidence},
                Reasoning: {toxicity_result.reasoning}
                """,
        )
        if hierarchical_result:
            return {
                "compound_prioritization": {
                    "result": result.toDict(),
                    "sub_agents": {
                        "cf_efficacy": {"result": efficacy_result.toDict()},
                        "toxicity_screening": {"result": toxicity_result.toDict()},
                    },
                }
            }
        else:
            return result


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")

    dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash-preview-05-20", temperature=0.5))

    agent = CompoundPrioritizationAgent()
    result = agent.forward(compound_name="Givinostat", hierarchical_result=True)
    print(result)

    dspy.inspect_history(n=5)
