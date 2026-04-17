---
name: quote-feedback-capture-skill
slug: quote-feedback-capture-skill
version: 1.0.0
author: "BaoJia Team"
description: 将用户对报价草案的修改意见转成结构化反馈事件、偏好候选和规则候选。当用户提到记录报价反馈、保存修改意见、沉淀客户偏好、生成规则候选时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-feedback-capture-skill

## When to Use（何时使用）

- 已经有报价草案或最终 `quote_document`
- 需要将用户修改意见结构化为可存储反馈事件
- 需要为后续反馈飞轮沉淀案例、偏好和规则候选

## When NOT to Use（何时不用）

- 还没有任何报价上下文
- 只是要生成报价，不是要记录反馈
- 只是要检索已存在反馈记忆

## Quick Start（快速开始）

运行命令：`python run.py --input samples/sample-input.json --output out/sample-output.json`

## Core Behavior（核心行为）

- 只做反馈结构化，不做报价生成
- 输出 `feedback_events`、`case_memory_patch`、`preference_candidates`、`rule_candidates`
- 反馈必须绑定到结构化 target
- 不直接修改正式规则配置
