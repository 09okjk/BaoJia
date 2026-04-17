---
name: quote-feedback-rule-review-skill
slug: quote-feedback-rule-review-skill
version: 1.0.0
author: "BaoJia Team"
description: 审核 feedback memory 中已准备好的规则候选，决定批准或拒绝，并将批准结果写入 approved rules。当用户提到审核规则候选、批准偏好规则、拒绝候选规则时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-feedback-rule-review-skill

## When to Use（何时使用）

- 需要审核 `.opencode/memory/rule-candidates` 中的候选规则
- 需要将候选批准为正式 approved rule
- 需要记录拒绝原因或审批人信息

## When NOT to Use（何时不用）

- 只是要记录反馈，不是要审核规则
- 还没有形成 rule candidate
- 只是要检索已审核规则

## Core Behavior（核心行为）

- 读取 rule candidate
- 支持 `approve` 或 `reject`
- 审批通过时写入 `.opencode/memory/approved-rules`
- 回写原 rule candidate 状态
