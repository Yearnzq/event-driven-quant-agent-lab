# Phase 1 MCP 策略

日期：2026-05-03

## 结论

Phase 1 默认不接外部 MCP。根目录 `.mcp.json` 故意保持为空：

```json
{
  "mcpServers": {}
}
```

原因是当前阶段的核心目标是离线可复现闭环，而不是外部系统接入。完成判据来自仓库本身：

- `python -m pytest -q`
- `python -m compileall -q src`
- `python scripts/stage_01_gate.py`
- Markdown/JSON/audit artifacts
- 人工阶段审查

## Phase 1 允许的上下文来源

- 仓库内文档、源码、测试、脚本。
- 容器内离线命令输出。
- 用户显式提供的 issue、日志、错误栈或审查要求。
- 官方技术文档，只读查询。

## Phase 1 不接的 MCP

- 交易所账户、broker、订单、持仓写接口。
- 生产数据库。
- secret manager。
- 云资源管理写接口。
- 自动部署、自动回滚、自动发布工具。
- 未清洗新闻、网页、社媒全文入口。
- 任何能修改风控参数、创建订单或绕过人工审查的工具。

## 后续可接的只读 MCP

进入 Phase 2+ 后，可以按收益逐个接入：

| MCP | 权限 | 用途 |
| --- | --- | --- |
| GitHub Issues / PRs | read-only | 拉需求、diff、review context |
| CI logs | read-only | 失败分诊和证据采集 |
| Docs / handbook | read-only | 查团队规范和设计文档 |
| Official technical docs | read-only | 查 OpenAI、PydanticAI、NautilusTrader 等官方资料 |

写权限必须另行设计审批策略，不随 MCP 默认开启。

## Agent 使用规则

Agent 不能因为 MCP 返回了外部内容就绕过 Data Gate、Risk Gate 或文本清洗边界。外部内容只作为上下文，进入系统产物前仍必须满足：

- 有来源。
- 有时间戳。
- 有 evidence id 或可生成 evidence id。
- 没有泄漏 raw body / HTML / secret。
- 不改变 `order_allowed=false` 和 `human_required=true`。

## 可参考的外部 harness 仓库

[`affaan-m/everything-claude-code`](https://github.com/affaan-m/everything-claude-code) 可以作为二级参考，主要参考它的目录拆分和 harness 思路：

- `AGENTS.md` / `RULES.md` 的常驻规则组织方式。
- `skills/` 优先于 slash commands 的 workflow surface 思路。
- hooks 的触发点设计，但 Phase 1 不直接启用。
- MCP 配置的“少量启用、禁用不用工具”的上下文控制思路。
- security guide 里的 prompt injection、secret path、MCP、hooks 和 sandbox 风险提示。

不要直接照搬：

- full install profile。
- broad MCP config。
- 自动化 hooks。
- subagent orchestration。
- 任何与生产写操作、部署、浏览器控制、数据库写入、secret 访问相关的配置。

对本项目来说，它是 harness 设计素材，不是工程完成判据。完成判据仍然是本仓库的 tests、stage gate、artifact、audit 和 human review。
