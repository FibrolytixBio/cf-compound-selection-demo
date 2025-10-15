import os

import pandas as pd
import dspy

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

LITL_DATA_PATH = os.path.join(os.path.dirname(__file__), "litl_data.csv")
LITL_REFLECTIONS_PATH = os.path.join(
    os.path.dirname(__file__), "1.no_litl_reflections.pkl"
)


def load_efficacy_devset(path=LITL_DATA_PATH, uniform_efficacy=False):
    df = pd.read_csv(path)
    if uniform_efficacy:
        df = df.sort_values("cf_efficacy", ascending=False)
        df = df.head(25)

    devset = []
    for _, row in df.iterrows():
        example = dspy.Example(
            compound_name=row["compound_name"], cf_efficacy=row["cf_efficacy"]
        ).with_inputs("compound_name")
        devset.append(example)
    return devset


### Summarization module for LITL runs ###


class SummarizeRun(dspy.Signature):
    """Produce a concise MARKDOWN of the run. Summarize information where possible to make it more concise, but never lose information.

    FORMAT:
    ## Compound
    <compound_name>

    ## Trajectory
    - Step 0:
        - <reasoning>
        - <tool>
        - <observation>
    - Step 1: ...

    ## Reasoning
    <reasoning text>

    ## Predicted Efficacy
    <predicted_efficacy>

    ## Confidence
    <confidence>
    """

    compound_name: str = dspy.InputField(
        desc="The name of the compound being evaluated"
    )
    trajectory: str = dspy.InputField(desc="The raw trace data to summarize")
    reasoning: str = dspy.InputField(
        desc="The reasoning used to arrive at the trace conclusion."
    )
    predicted_efficacy: float = dspy.InputField(
        desc="The predicted efficacy of the compound."
    )
    confidence: float = dspy.InputField(desc="The confidence level prediction.")
    summary: str = dspy.OutputField(
        desc="A concise, structured summary of key information formatted for use by ReAct agent LLM"
    )


summarizer_lm = dspy.LM(
    "gemini/gemini-2.5-flash-lite", temperature=0.0, cache=True, max_tokens=25000
)

summarizer_module = dspy.Predict(SummarizeRun)

### Reflection module for LITL runs ###


class ReflectRun(dspy.Signature):
    """Calculate the error of the run as the absolute difference between the predicted efficacy and the real efficacy.
    Then, produce a thorough reflection as to why the error occurred and how to improve the prediction accuracy in future runs.

    FORMAT:
    ## Real Efficacy
    <real efficacy>

    ## Error
    <|predicted efficacy - real efficacy|>

    ## Error Reasoning
    <error reasoning text>

    ## Improvements
        1) <improvement 1>
        2) <improvement 2>
        3) ...
    """

    summarized_run: str = dspy.InputField(desc="The the run being evaluated")
    real_efficacy: float = dspy.InputField(desc="The actual efficacy of the compound.")
    reflection: str = dspy.OutputField()


reflection_lm = dspy.LM(
    "gemini/gemini-2.5-pro", temperature=0.5, cache=True, max_tokens=25000
)

reflection_module = dspy.Predict(ReflectRun)
