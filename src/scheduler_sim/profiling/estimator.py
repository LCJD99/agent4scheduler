from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from scheduler_sim.domain.resources import ResourceVector


SCENE_COMPLEXITY_TO_NUMERIC = {
    "small": 1.0,
    "medium": 2.0,
    "large": 3.0,
}


@dataclass(slots=True)
class ProfilingEstimator:
    models: dict[str, Pipeline]
    source_path: Path

    @classmethod
    def from_csv(cls, path: str | Path) -> "ProfilingEstimator":
        csv_path = Path(path)
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)

        dataframe = pd.read_csv(csv_path)
        if "status" in dataframe.columns:
            dataframe = dataframe[dataframe["status"] == "success"].copy()

        required_columns = {
            "tool_name",
            "cpu_core",
            "cpu_memory_mb",
            "gpu_memory_mb",
            "network_bandwidth_mbps",
            "input_size",
        }
        missing_columns = required_columns.difference(dataframe.columns)
        if missing_columns:
            raise ValueError(
                f"Profiling CSV missing required columns: {sorted(missing_columns)}"
            )

        latency_column = (
            "latency_us" if "latency_us" in dataframe.columns else "latency"
        )
        if latency_column not in dataframe.columns:
            raise ValueError("Profiling CSV must contain latency or latency_us column")

        models: dict[str, Pipeline] = {}
        for tool_name, group in dataframe.groupby("tool_name"):
            x_values = cls._feature_matrix(
                cpu_core=group["cpu_core"].astype(float).to_numpy(),
                cpu_memory_mb=group["cpu_memory_mb"].astype(float).to_numpy(),
                gpu_memory_mb=group["gpu_memory_mb"].astype(float).to_numpy(),
                network_bandwidth_mbps=group["network_bandwidth_mbps"]
                .astype(float)
                .to_numpy(),
                scene_complexity=group["input_size"].astype(str).tolist(),
            )
            y_values = np.log(group[latency_column].astype(float).to_numpy() + 1e-6)
            model = Pipeline(
                [
                    ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                    ("scaler", StandardScaler()),
                    (
                        "ridge",
                        RidgeCV(alphas=[1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100]),
                    ),
                ]
            )
            model.fit(x_values, y_values)
            models[str(tool_name)] = model

        return cls(models=models, source_path=csv_path)

    def estimate_latency_us(
        self,
        *,
        tool_name: str,
        allocated_resources: ResourceVector,
        scene_complexity: str,
    ) -> int:
        model = self.models.get(tool_name)
        if model is None:
            raise KeyError(f"Missing profiling model for tool {tool_name}")

        features = self._feature_matrix(
            cpu_core=np.array([allocated_resources.cpu_cores], dtype=float),
            cpu_memory_mb=np.array([float(allocated_resources.memory_mb)], dtype=float),
            gpu_memory_mb=np.array([float(allocated_resources.gpu_vram_mb)], dtype=float),
            network_bandwidth_mbps=np.array([allocated_resources.network_mbps], dtype=float),
            scene_complexity=[scene_complexity],
        )
        predicted_log_latency = float(model.predict(features)[0])
        predicted_latency = float(np.exp(predicted_log_latency))
        return max(1, int(round(predicted_latency)))

    @classmethod
    def _feature_matrix(
        cls,
        *,
        cpu_core: np.ndarray,
        cpu_memory_mb: np.ndarray,
        gpu_memory_mb: np.ndarray,
        network_bandwidth_mbps: np.ndarray,
        scene_complexity: list[str],
    ) -> np.ndarray:
        complexity_values = np.array(
            [cls._complexity_to_numeric(value) for value in scene_complexity],
            dtype=float,
        )
        return np.column_stack(
            [
                np.log(cpu_core + 1e-6),
                np.log(cpu_memory_mb + 1e-6),
                np.log(gpu_memory_mb + 1e-6),
                np.log(network_bandwidth_mbps + 1e-6),
                np.log1p(complexity_values),
            ]
        )

    @staticmethod
    def _complexity_to_numeric(value: str) -> float:
        try:
            return SCENE_COMPLEXITY_TO_NUMERIC[value]
        except KeyError as exc:
            raise ValueError(
                f"scene_complexity must be one of {sorted(SCENE_COMPLEXITY_TO_NUMERIC)}"
            ) from exc
