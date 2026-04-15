---
name: historical-quote-reference-skill
slug: historical-quote-reference-skill
version: 1.0.0
author: "BaoJia Team"
description: 基于 quote_request 和 quotable_items 检索相似历史报价案例，输出 matches、reference_summary 和 confidence。当用户提到历史报价参考、相似案例检索、价格带参考、remark 模式参考时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
      env: ["DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "HIST_EMBED_MODEL", "HIST_EMBED_DIMENSIONS", "HIST_EMBED_TIMEOUT_SECONDS"]
    os: ["win32"]
---

# historical-quote-reference-skill

## When to Use（何时使用）

- 已有 `quote_request`
- 已有 `quotable_items`
- 需要检索历史相似报价案例并提炼价格带与 remark 模式参考

## When NOT to Use（何时不用）

- 还没有完成可报价判断
- 已进入最终金额计算或最终报价单生成

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "quote_request": {},
  "quotable_items": []
}
```

最小输出骨架：

```json
{
  "matches": [],
  "reference_summary": {},
  "confidence": 0.0
}
```

## Core Behavior（核心行为）

- 只提供历史参考，不直接给出最终报价金额或 remark 结论
- 输出 `matches`、`reference_summary`、`confidence`
- 每个匹配结果都必须保留可解释原因
- embedding 不可用时必须可回退到本地检索策略

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 结构契约：`references/REFERENCE_CONTRACT.md`
- 正式 Schema：`references/historical-quote-reference-input.schema.json`、`references/historical-quote-reference-output.schema.json`
- 检索规则：`references/RETRIEVAL_RULES.md`
- 详细示例：`references/EXAMPLES.md`
- 详细设计：`设计与规范/historical_quote_reference_skill 详细设计.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/historical_quote_reference_skill/scripts/main.py" --input ".opencode/skills/historical_quote_reference_skill/samples/sample-input.json"`
- 如需 embedding，先复制 `.env.example` 为本地环境配置并填写 API Key

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过 schema 校验，可选

## Core Rules（核心规则）

- 历史结果只提供参考，不直接等同最终定价
- 必须保留命中特征和相似度解释
- 缓存、embedding 与回退策略要保持可预测

## Security & Privacy（安全说明）

- 默认在本地处理历史样本和缓存
- 若启用 DashScope embedding，会向外部模型接口发送检索文本
- 不应把真实密钥提交到版本库

## Related Skills（相关技能）

- `quote-feasibility-check-skill`
- `quote-pricing-skill`
- `quote-review-output-skill`

## Feedback（反馈）

- 修改检索策略时同步更新 `references/RETRIEVAL_RULES.md`
- 修改环境变量要求时同步更新 `.env.example`、`references/*.schema.json` 与 `samples/`
