---
name: quote-feedback-reference-skill
slug: quote-feedback-reference-skill
version: 1.0.0
author: "BaoJia Team"
description: 在生成报价前检索与当前项目相似的反馈记忆，输出适用偏好、禁止模式、建议调整和审核提醒。当用户提到反馈记忆检索、客户偏好继承、草案优化建议时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-feedback-reference-skill

## When to Use（何时使用）

- 已经完成 `quote_request` 标准化
- 需要在生成报价前检索历史反馈记忆
- 需要获得客户偏好、负样本和审核提醒

## When NOT to Use（何时不用）

- 还没有 `quote_request`
- 只是要记录反馈，不是检索反馈
- 只需要历史报价参考，而不是用户反馈记忆

## Quick Start（快速开始）

运行命令：`python run.py --input samples/sample-input.json --output out/sample-output.json`

## Core Behavior（核心行为）

- 从本地 feedback memory 目录加载记忆记录
- 先按结构化上下文过滤，再生成匹配建议
- 输出 `matches`、`applicable_preferences`、`forbidden_patterns`、`recommended_adjustments`、`review_alerts`
- 不直接修改正式报价内容
