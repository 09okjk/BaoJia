# Line Mapping Rules

## 目的

定义第四个 Skill 第一版的 line 建模口径。

## 可报价项

优先映射为：

- `line_type = priced`
- `pricing_mode = lump_sum` 或 `unit_price`
- `status = chargeable`

## 待确认项

优先映射为：

- `line_type = pending`
- `pricing_mode = pending`
- `status = pending`
- `amount_display = Pending`

## 船东提供 / 排除项

优先映射为：

- `line_type = note`
- `pricing_mode = text_only`
- `status = by_owner` 或 `excluded`

## 按实际 / 额外收费

优先映射为：

- `status = as_actual` / `extra`
- `amount_display = As actual` / `Extra`
