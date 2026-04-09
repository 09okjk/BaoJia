# Feasibility Contract

## 目的

定义 `quote_feasibility_check_skill` 的推荐输出结构，供实现和联调使用。

## 输入

```json
{
  "quote_request": {}
}
```

## 输出

```json
{
  "can_quote": true,
  "quote_scope": "full | partial | not_ready",
  "quotable_items": [],
  "tbc_items": [],
  "exclusions": [],
  "missing_fields": [],
  "questions_for_user": [],
  "review_flags": []
}
```

## 项目判断结构

推荐 `quotable_items`、`tbc_items`、`exclusions` 都采用同一结构：

```json
{
  "item_id": "",
  "item_type": "service | spare_parts | other",
  "title": "",
  "decision": "quotable | tbc | excluded",
  "reason": "",
  "blocking_fields": [],
  "suggested_status": "chargeable | pending | by_owner | excluded | if_needed",
  "source": "quote_request.candidate_items"
}
```

## questions_for_user 推荐结构

```json
{
  "question_id": "",
  "target": "customer | internal",
  "topic": "",
  "question": "",
  "related_item_ids": []
}
```

## review_flags 推荐结构

```json
{
  "flag_code": "",
  "severity": "high | medium | low",
  "message": "",
  "related_item_ids": []
}
```

## 判断口径

- `full`：全部候选项均可报价
- `partial`：部分候选项可报价，部分待确认或排除
- `not_ready`：当前不建议进入正式报价

## 正式 Schema

- 输入 Schema：`../schemas/input.schema.json`
- 输出 Schema：`../schemas/output.schema.json`
