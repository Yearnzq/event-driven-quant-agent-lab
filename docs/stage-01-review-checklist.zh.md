# 阶段 1 审查清单：工程基线与离线可复现闭环

日期：2026-05-03

## 审查目标

确认项目已经具备稳定工程基线：容器能进入、环境可识别、离线测试可运行、核心 CLI 可复现、产物路径清晰、advisory-only 边界可自动检查。通过后再进入阶段 2：数据层硬化。

## 离线必查项

- [ ] 容器 `quant-agent-lab` 处于 running/healthy。
- [ ] conda 环境 `quant` 可激活，并记录 `python --version`。
- [ ] `python -m pytest -q` 通过。
- [ ] `python -m compileall -q src` 通过。
- [ ] sample CSV advisory pipeline 能生成 Markdown/JSON/audit 产物。
- [ ] `--csv-dir` 能读取 metadata 或默认文件名跑 CSV advisory pipeline。
- [ ] `--evaluate-signals` 能用 sample CSV 生成研究 Markdown/JSON。
- [ ] `--clean-news-jsonl` 输出不包含原始正文、HTML 或 `content` 字段。
- [ ] 报告中明确写明 advisory-only，不是自动交易指令。
- [ ] Phase 1 所有 recommendation/order 相关产物里 `order_allowed=false`。
- [ ] 不调用真实模型，不接 A2A，不接 NautilusTrader，不自动下单。
- [ ] `docs/requirements-alignment.zh.md` 已审查，确认当前路线没有偏成自动交易 bot 或纯报告工具。

## 联网 best-effort 项

- [ ] GitHub SSH 可访问，但不自动 commit/push。
- [ ] Binance 公开 Kline 下载可尝试。
- [ ] 如果 Binance 下载失败，记录 `BINANCE_CHECK=WAIVED_NETWORK_FAILURE`，不阻塞阶段 1。

## 推荐审查命令

基础环境和测试：

```bash
docker ps --filter name=quant-agent-lab

docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant

python --version
python -m pytest -q
python -m compileall -q src
'
```

离线阶段 1 自动门禁：

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant

python scripts/stage_01_gate.py
'
```

联网 best-effort 门禁：

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant

python scripts/stage_01_gate.py --try-binance
ssh -T -o BatchMode=yes git@github.com 2>&1 || true
'
```

## 自动断言覆盖

`scripts/stage_01_gate.py` 会自动检查：

- sample CSV advisory 产物存在。
- research Markdown/JSON 产物存在。
- cleaned text evidence 产物存在。
- 报告和 JSON 产物包含 advisory-only / `order_allowed` 边界。
- 阶段 1 产物中不存在 `"order_allowed": true`。
- 清洗后的文本证据不包含 `content`、`raw_content`、HTML 标签。
- Binance 联网失败时输出 `BINANCE_CHECK=WAIVED_NETWORK_FAILURE`，不让阶段 1 失败。

## 通过标准

- 所有离线必查项通过。
- 联网项成功则记录为通过；失败则记录为 best-effort waiver。
- README、路线文档、审查清单足以让人工复现阶段 1。
- 没有新增自动提交、自动推送、自动下单、私钥/API key 写入仓库等行为。

## 不通过时的处理

- 如果测试失败：阶段 1 延后一天，只修测试和对应功能。
- 如果 `stage_01_gate.py` 离线门禁失败：阶段 1 延后一天，优先修边界断言对应功能。
- 如果 Binance 下载失败：不阻塞工程基线，阶段 2 继续补网络失败降级和多数据源策略。
- 如果文本清洗仍泄漏原始正文：阶段 1 延后，先修输入边界。
