# Phase 4 Review

日期：2026-05-04

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 5（风控规则增强），但需继续保持 advisory-only 边界。

## 2. 本阶段范围

Phase 4 聚焦信号研究框架：

- 默认 signal registry。
- 多信号离线评估。
- research ranking。
- research Markdown/JSON 报告。
- registry 显式记录每个 signal 的参数，用于审计和复现。
- research ranking 使用归一化 robust score：累计收益、平均信号收益、hit rate、最大回撤倒数和方向性覆盖率，不再使用单一 `cumulative_signal_return - max_drawdown`。
- research 输出接入 artifact catalog 和 run manifest。
- 独立 `stage_04_gate.py`。

未引入真实模型、A2A、NautilusTrader、paper/live trading、broker、secret、生产访问或自动下单。

## 3. 修改文件

- `README.md`
- `docs/stage-04-review-checklist.zh.md`
- `docs/reviews/phase-04-review.zh.md`
- `scripts/stage_04_gate.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/data/audit.py`
- `src/quant_agent_lab/research/evaluation.py`
- `tests/test_research_evaluation.py`

## 4. 新增或扩展的 schema

- `phase4.signal_research.v1`
  - `symbol`
  - `generated_at`
  - `strategy_count`
  - `summaries`
  - `ranking`
  - `ranking[].score_components`
  - `best_research_score_strategy`
  - `disclaimer`
- `deployable=false`
  - `order_allowed=false`
  - `human_required=true`

## 5. 新增用户可运行命令

```bash
python scripts/stage_04_gate.py
```

`--evaluate-signals` 现在会输出默认 registry 的多信号研究报告：

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --evaluate-signals \
  --csv-dir sample_data/btc_usdt \
  --output-dir artifacts/research
```

## 6. 产物路径

Phase 4 research 输出目录包含：

- `signal-registry.json`
- `signal_research_report.md`
- `signal_research_report.json`
- `ma_crossover_7_30_h1.md`
- `ma_crossover_7_30_h1.json`
- `breakout_20_h1.md`
- `breakout_20_h1.json`
- `volatility_regime_20_h1.md`
- `volatility_regime_20_h1.json`
- `artifact-catalog.json`
- `run-manifest.json`

## 7. 已运行命令

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
git status --short --branch
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant
python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-phase4-verify-20260504
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-phase4-verify-20260504
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-phase4-verify-20260504
python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-phase4-verify-20260504
'
```

## 8. 验证结果

- Python：`Python 3.10.20`
- pytest：`36 passed in 4.11s`
- compileall：`python -m compileall -q src` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-phase4-verify-20260504`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-02-phase4-verify-20260504`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-03-phase4-verify-20260504`
- Phase 4 gate：`STAGE_04_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-04-phase4-verify-20260504`
- Phase 4 gate 明细：
  - `SIGNAL_REGISTRY_CHECK=PASS`
  - `SIGNAL_RESEARCH_REPORT_CHECK=PASS`
  - `RESEARCH_ARTIFACT_CATALOG_CHECK=PASS`
  - `RESEARCH_TAMPER_CHECK=PASS`
  - `ORDER_ALLOWED_TRUE_COUNT=0`
  - `DEPLOYABLE_TRUE_COUNT=0`
  - `HUMAN_REQUIRED=true`

## 9. 边界确认

- no real model call：通过，仍为 deterministic research code。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret：通过。
- no auto order：通过。
- `order_allowed=false`：由 research schema 和 stage gate 断言。
- `human_required=true`：由 research schema 和 stage gate 断言。
- `deployable=false`：由 research schema 和 stage gate 断言。
- raw text leakage：本阶段未新增文本输入路径。

## 10. 剩余风险

- research score 是 deterministic smoke ranking，不代表策略有效性、可交易性或可部署性。
- 当前 registry 覆盖 MA crossover、breakout、volatility regime；更多信号族可在后续迭代扩展。
- Phase 4 robust score 仍是离线研究排序信号，不代表可部署性；Phase 10 会使用更完整的 walk-forward / stress / cost sensitivity 评分。

## 11. 2026-05-06 Claude Review Follow-up

- Claude review P2：原 `research_score = cumulative_signal_return - max_drawdown` 可能让高风险高收益策略排名靠前。
- 处理结果：已改为多维归一化 robust score，并将 score components 写入 JSON/Markdown 审计产物。
- 新 score components：
  - `cumulative_return_rank`
  - `average_return_rank`
  - `hit_rate_rank`
  - `drawdown_inverse_rank`
  - `directional_coverage_rank`
- 边界不变：`deployable=false`、`order_allowed=false`、`human_required=true`。
- 验证命令：
  ```bash
  docker exec quant-agent-lab bash -lc '
  cd /workspace/event-driven-quant-agent-lab
  source /opt/miniconda3/etc/profile.d/conda.sh
  conda activate quant
  python --version
  python -m pytest -q
  python -m compileall -q src
  python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-prepush-20260506
  python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-prepush-20260506
  python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-prepush-20260506
  python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-prepush-20260506
  python scripts/stage_05_gate.py --output-dir /tmp/qal-stage-05-prepush-20260506
  '
  ```
- 验证结果：`41 passed in 3.16s`，compileall PASS，Phase 1/2/3/4/5 gates 全部 PASS。
