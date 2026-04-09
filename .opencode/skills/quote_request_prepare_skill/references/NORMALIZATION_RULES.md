# Normalization Rules

## 目的

定义 `quote_request_prepare_skill` 中允许执行的标准化动作，以及必须避免的越界动作。

## 允许的标准化动作

### 1. 币种标准化

允许把不同表达统一为标准币种代码，例如：

- `usd`
- `US Dollar`
- `US DOLLAR`

归一为：

- `USD`

### 2. 服务模式标准化

允许把自然语言服务模式统一为稳定枚举，例如：

- `voyage repair` -> `voyage_repair`
- `航修` -> `voyage_repair`
- `厂修` -> `dock_repair`

### 3. 地点类型标准化

允许把地点表述统一到抽象类型，例如：

- 码头 -> `port`
- 锚地 -> `anchorage`
- 船厂 -> `shipyard`
- 航行中 / 随航 -> `underway`

### 4. 候选项去重与归并

允许合并以下重复信息：

- 同一设备、同一工作标题重复出现
- 同一工作范围在多个段落重复描述

归并时要求：

- 保留主标题
- 保留主要工作范围
- 把归并动作写入 `normalization_flags`

### 5. 文本清洗

允许做轻量文本清洗：

- 去掉前后空白
- 去掉重复空行
- 去掉无意义噪声前缀

## 禁止的动作

### 1. 默认补全业务事实

禁止：

- 猜测船型
- 猜测服务日期
- 猜测客户要求的币种

### 2. 提前做可报价判断

禁止在本 Skill 中输出：

- can quote
- partial quote
- exclusion

### 3. 提前做定价结论

禁止在本 Skill 中输出：

- 金额
- 折扣
- summary
- 最终收费状态

### 4. 把待确认项伪装成确定事实

例如“备件可能船东提供”，不能直接改写成已确认的 `by_owner` 结论。

## normalization_flags 推荐结构

```json
[
  {
    "flag_code": "normalized_currency_code",
    "field": "header_context.currency",
    "from": "US DOLLAR",
    "to": "USD",
    "reason": "统一币种编码"
  }
]
```

## 常见 flag_code 建议

- `normalized_currency_code`
- `normalized_service_mode`
- `normalized_location_type`
- `merged_duplicate_candidate_items`
- `resolved_input_conflict`
- `cleaned_text_noise`
