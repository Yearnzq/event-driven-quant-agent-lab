# Phase 1 Review

日期：2026-05-03

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可以进入 Phase 2（数据层硬化），但继续保持 advisory-only 边界。

## 2. 已运行命令

- docker ps：`quant-agent-lab` running / healthy，镜像 `quant-agent-lab-dev:latest`。
- python --version：`Python 3.10.20`。
- pytest：`python -m pytest -q`，结果 `29 passed in 3.20s`。
- compileall：`python -m compileall -q src`，退出码 0，无编译错误输出。
- stage_01_gate：`python scripts/stage_01_gate.py`，结果 `STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-gate`，`BINANCE_CHECK=SKIPPED`。
- clean review gate：`python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-review-20260503`，结果 `STAGE_01_OFFLINE_GATE=PASS`。
- GitHub SSH：未运行；本次未要求联网 best-effort 检查。
- Binance download：未运行；本次未要求联网 best-effort 检查。

完整离线验证命令：

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant

python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py
'
```

## 3. 产物路径

- reports：`/tmp/qal-stage-01-review-20260503/reports/mock/`，`/tmp/qal-stage-01-review-20260503/reports/csv/`
- research：`/tmp/qal-stage-01-review-20260503/research/ma_crossover_7_30_h1.md`，`/tmp/qal-stage-01-review-20260503/research/ma_crossover_7_30_h1.json`
- evidence：`/tmp/qal-stage-01-review-20260503/evidence/cleaned_news.jsonl`
- audit：`/tmp/qal-stage-01-review-20260503/reports/mock/audit-log.jsonl`，`/tmp/qal-stage-01-review-20260503/reports/csv/audit-log.jsonl`
- sample CSV：`/tmp/qal-stage-01-review-20260503/sample/bars_1h.csv`，`/tmp/qal-stage-01-review-20260503/sample/bars_1d.csv`，`/tmp/qal-stage-01-review-20260503/sample/portfolio.json`

## 4. Schema / 边界变更

- 新增 schema：本次审查未新增 schema。
- 修改 schema：本次审查未修改 schema。
- 禁止边界确认：
  - no real model call：通过，Phase 1 只使用 mock TypedAgents。
  - no A2A：通过，未引入 A2A 服务或 MCP 写入链路。
  - no NautilusTrader：通过，未接 NautilusTrader adapter。
  - no paper trading：通过，未生成 paper trading 行为或订单草稿。
  - no auto order：通过，未自动下单。
  - `order_allowed=false`：通过，抽查产物中 `"order_allowed": true` 计数为 0。
  - `human_required=true`：通过，抽查产物中 `"human_required": false` 计数为 0；mock / CSV 报告 JSON 均为 `human_required=true`。
  - no raw news/web body enters agent context：通过，`cleaned_news.jsonl` 不包含 `content`、`raw_content` 或 HTML 标签。

## 5. 测试覆盖

- Data Gate：由 `tests/test_gates.py` 和 stage gate 覆盖，失败路径输出 `insufficient_evidence`。
- Risk Gate：由 `tests/test_gates.py` 和 stage gate 覆盖，Phase 1 不允许订单。
- mock agents：由 pipeline 测试和 stage gate 覆盖。
- report：stage gate 验证 Markdown / JSON advisory-only 边界。
- audit：测试和 stage gate 生成 JSON / JSONL audit 产物。
- signal evaluation：stage gate 生成 `ma_crossover_7_30_h1` Markdown / JSON 研究产物。
- news cleaning：stage gate 验证清洗输出不泄漏原始正文、HTML 或 raw 字段。

## 6. 风险和遗留问题

- Binance 网络：本次未运行联网 best-effort；网络失败按清单不阻塞 Phase 1。
- GitHub SSH：本次未运行联网 best-effort；未 commit、未 push、未创建 PR。
- Python 3.10 / NautilusTrader Python 3.12+：当前 Phase 1 保持 Python 3.10.20 兼容；NautilusTrader 仍属于后续 adapter 阶段。
- 当前 signal evaluation 只是 smoke test：已证明离线研究产物可生成，尚未代表策略有效性或可部署性。
- worktree：仓库已有大量未提交 / 未跟踪文件；本次只填写 review memo，不回滚既有改动。

## 7. 下一阶段建议

- 是否进入 Phase 2：可以。
- Phase 2 优先修复：
  - 数据层 schema / manifest / hash catalog 硬化。
  - 多数据源失败降级和样本数据版本化。
  - 继续保持 `order_allowed=false`、`human_required=true`。
  - 继续禁止真实模型 API、A2A、NautilusTrader、paper trading、自动下单和 secret 读取。

## 8. 2026-05-03 Codex 复核证据

- 当前阶段判断：`docs/ten-stage-roadmap.zh.md` 仍标注今日阶段为 Phase 1；现有 review memo 结论为 PASS，可进入 Phase 2，但本次只复核并固化 Phase 1 证据，未引入 Phase 2 范围变更。
- worktree 状态：已有大量未提交/未跟踪文件，视为既有工作；本次只更新本 review memo，不回滚、不 commit、不 push。
- 容器状态：`quant-agent-lab` running / healthy，镜像 `quant-agent-lab-dev:latest`。
- 验证命令：
  ```bash
  docker exec quant-agent-lab bash -lc '
  cd /workspace/event-driven-quant-agent-lab
  source /opt/miniconda3/etc/profile.d/conda.sh
  conda activate quant
  python --version
  python -m pytest -q
  python -m compileall -q src
  python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-codex-20260503
  '
  ```
- Python：`Python 3.10.20`。
- pytest：`29 passed in 2.90s`。
- compileall：`python -m compileall -q src` 退出码 0，无编译错误输出。
- Stage gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-codex-20260503`，`BINANCE_CHECK=SKIPPED`。
- 产物路径：
  - reports：`/tmp/qal-stage-01-codex-20260503/reports/mock/`，`/tmp/qal-stage-01-codex-20260503/reports/csv/`
  - research：`/tmp/qal-stage-01-codex-20260503/research/ma_crossover_7_30_h1.md`，`/tmp/qal-stage-01-codex-20260503/research/ma_crossover_7_30_h1.json`
  - evidence：`/tmp/qal-stage-01-codex-20260503/evidence/cleaned_news.jsonl`
  - audit：`/tmp/qal-stage-01-codex-20260503/reports/mock/audit-log.jsonl`，`/tmp/qal-stage-01-codex-20260503/reports/csv/audit-log.jsonl`
  - sample CSV：`/tmp/qal-stage-01-codex-20260503/sample/bars_1h.csv`，`/tmp/qal-stage-01-codex-20260503/sample/bars_1d.csv`，`/tmp/qal-stage-01-codex-20260503/sample/portfolio.json`
- 边界抽查：
  - `ORDER_ALLOWED_TRUE_COUNT=0`
  - `HUMAN_REQUIRED_FALSE_COUNT=0`
  - `CLEANED_NEWS_ROWS=1 RAW_BODY_FIELD_LEAKS=0 HTML_LEAKS=0`
- 禁止边界确认：未接真实模型 API，未接 A2A，未接 NautilusTrader，未做 paper/live trading，未自动下单，未读取 secret，未引入写权限 MCP，未把未清洗新闻/网页/社媒全文放进 agent context。
- 剩余风险：本次未运行 Binance/GitHub SSH best-effort 网络检查；按 Phase 1 checklist，网络失败或跳过不阻塞离线工程基线。当前 research evaluation 仍是 smoke test，不代表策略有效性或可部署性。
