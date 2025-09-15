import os

import pandas as pd
import dspy

LITL_DATA_PATH = os.path.join(os.path.dirname(__file__), "litl_data.csv")


def load_efficacy_devset(path=LITL_DATA_PATH):
    df = pd.read_csv(path)
    devset = []
    for _, row in df.iterrows():
        example = dspy.Example(
            compound_name=row["compound_name"], cf_efficacy=row["cf_efficacy"]
        ).with_inputs("compound_name")
        devset.append(example)
    return devset
