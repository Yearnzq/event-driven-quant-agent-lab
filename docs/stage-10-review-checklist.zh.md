# Stage 10 Review Checklist

日期：2026-05-07

## 范围

Stage 10 聚焦离线综合回测、鲁棒性验收与交易引擎适配前置：

- 固定 strategy style registry。
- 固定 walk-forward train/validation/test split。
- 固定成本模型：low / medium / high。
- 运行成本敏感性、压力测试、参数扰动和执行延迟测试。
- 运行 AI blind preference check，且只能使用 train/validation 摘要。
- 生成 tournament report、walk-forward、stress、cost、simulation manifest。
- 生成 NautilusTrader 只读 adapter input sample。
- 全部产物必须保持 research/advisory-only。

## 必跑命令

```bash
python -m pytest -q
python -m compileall -q src scripts
python scripts/stage_01_gate.py
python scripts/stage_02_gate.py
python scripts/stage_03_gate.py
python scripts/stage_04_gate.py
python scripts/stage_05_gate.py
python scripts/stage_06_gate.py
python scripts/stage_07_gate.py
python scripts/stage_08_gate.py
python scripts/stage_09_gate.py
python scripts/stage_10_gate.py
```

## 验收点

- `STRATEGY_STYLE_REGISTRY_CHECK=PASS`
- `WALK_FORWARD_SPLIT_CHECK=PASS`
- `COST_SENSITIVITY_CHECK=PASS`
- `STRESS_TEST_CHECK=PASS`
- `AI_BLIND_PREFERENCE_CHECK=PASS`
- `SIMULATION_MANIFEST_CHECK=PASS`
- `NAUTILUS_ADAPTER_SAMPLE_CHECK=PASS`
- `DEPLOYABLE_TRUE_COUNT=0`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

## 必须存在的产物

```text
strategy_style_tournament.md
strategy_style_tournament.json
walk_forward_results.json
stress_test_results.json
cost_sensitivity_results.json
simulation_manifest.json
adapter_input_sample.json
```

## 禁止边界

- 不自动下单。
- 不进入 paper/live trading。
- 不根据 test set 修改参数。
- 不把收益率最高策略标记为 deployable。
- 不接 broker、account、API key 或私钥。
- 不使用未经清洗的新闻/网页正文。
- NautilusTrader 本阶段只生成只读 adapter 样例，不做执行系统。
