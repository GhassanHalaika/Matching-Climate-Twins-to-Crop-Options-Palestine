from __future__ import annotations

import pandas as pd

from .config import DEFAULT_WEIGHTS, MetricWeights


def weighted_twin_distance(
    target: pd.Series,
    candidates: pd.DataFrame,
    weights: MetricWeights = DEFAULT_WEIGHTS,
) -> pd.DataFrame:
    metric_weights = weights.__dict__
    available = [col for col in metric_weights if col in target.index and col in candidates.columns]
    if not available:
        raise ValueError("No shared metric columns found between target and candidates.")

    scales = candidates[available].std(numeric_only=True).replace(0, 1).fillna(1)
    output = candidates.copy()
    distance = 0
    for col in available:
        diff = (output[col] - target[col]) / scales[col]
        distance = distance + metric_weights[col] * (diff**2)
        output[f"delta_{col}"] = output[col] - target[col]
    output["climate_distance"] = distance.pow(0.5)
    output["similarity_score"] = 100 / (1 + output["climate_distance"])
    return output.sort_values("climate_distance").reset_index(drop=True)

