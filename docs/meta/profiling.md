# Tool profiling

```python
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_percentage_error

features = [
    "cpu_cores",
    "cpu_memory_mb",
    "gpu_sram_mb",
    "network_bandwidth_mbps",
    "scene_complexity",
]

target = "latency_us"

df = pd.read_csv("profiling_data.csv")

# 只使用成功运行的样本
df = df[df["status"] == "success"].copy()

X_raw = df[features].values.astype(float)
y_raw = df[target].values.astype(float)

# log transform
X_log = np.zeros_like(X_raw)

X_log[:, 0] = np.log(X_raw[:, 0] + 1e-6)      # cpu cores
X_log[:, 1] = np.log(X_raw[:, 1] + 1e-6)      # cpu memory
X_log[:, 2] = np.log(X_raw[:, 2] + 1e-6)      # gpu sram
X_log[:, 3] = np.log(X_raw[:, 3] + 1e-6)      # bandwidth
X_log[:, 4] = np.log1p(X_raw[:, 4])           # scene complexity

y_log = np.log(y_raw + 1e-6)

model = Pipeline([
    ("poly", PolynomialFeatures(degree=2, include_bias=False)),
    ("scaler", StandardScaler()),
    ("ridge", RidgeCV(alphas=[1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100]))
])

model.fit(X_log, y_log)

y_pred_log = model.predict(X_log)
y_pred = np.exp(y_pred_log)

mape = mean_absolute_percentage_error(y_raw, y_pred)

print("MAPE:", mape)
print("Best alpha:", model.named_steps["ridge"].alpha_)
```


## profiling csv

```
tool_name,cpu_core,cpu_memory_mb,gpu_memory_mb,network_bandwidth_mbps,input_size,latency
```

其中数据类型如下：

tool_name: string
cpu_core: float
cpu_memory_mb: float
gpu_memory_mb: float
network_bandwidth_mbps: float
input_size: ["small", "medium", "large"]

input_size 用于表示场景的复杂度

## 文件组织

profiling 文件放在 `data/profiling_data.csv` 中，其中 `tool_name` 需要和 `configs/tools/xx.yaml` 中的 `metadata:name 严格对应`

## 注意事项

- 无论关键型任务，还是 Agent 工具，都是同样的 profiling 方式，只是在 yaml 文件中区分其关键度，关键任务带有频率属性
