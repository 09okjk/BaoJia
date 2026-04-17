# 智能报价 Agent Skill 设计说明书（V2.2）

## 1. 文档目标

本文档用于定义“服贸报价 Agent”的能力边界、Skill 划分、输入输出协议、模板约束、编排方式与实施建议，目标是将服贸部报价业务流程沉淀为一组**职责明确、可组合、可扩展、符合 Agent Skill 最佳实践**的技能体系。

相较于前版，本版进一步明确：

> **智能报价 Agent 的最终目标，是基于智能评估结果、历史报价数据和报价规则，生成符合固定报价模板结构的 `QuoteDocument JSON`。**

本版重点解决以下问题：

- 输出不再停留于抽象报价草案，而是直接面向固定报价模板
- 报价单表头、明细列、表尾字段均有明确约束
- 支持单方案报价与多方案报价
- 支持折扣列
- 支持金额、待定、按实际、代理安排等多种呈现状态
- 支持方案级 summary 与表尾 footer summary 的分层表达

---

## 2. 设计背景

当前业务已经具备以下基础条件：

### 2.1 已有智能评估 Agent
目前已经有一个智能评估 Agent，能够生成评估单。评估单已包含服贸人员报价所需的大部分核心信息，例如：

- 船舶基础信息
- 服务项信息
- 服务内容与施工任务
- 工种、人数、工时
- 风险提示
- 工具 / 耗材 / 专用工具建议
- 备件需求
- 审核关注点
- 待确认事项

因此，智能报价 Agent 不需要再从原始询价邮件开始完整理解需求，而应以评估单作为主输入，聚焦于结构化报价生成。

### 2.2 已有历史报价数据库
目前已经有保存历史报价单结构化数据的数据库，可用于支持：

- 相似历史报价检索
- 历史价格区间参考
- 常见报价项参考
- 常见附加费用参考
- remark 模板参考
- 成交 / 未成交经验参考

### 2.3 报价模板已具备稳定骨架
当前报价单已经具备较稳定的模板结构，至少包括：

- 固定表头字段
- 固定中间报价列
- 固定表尾汇总区
- 固定备注区
- 固定服务支付条款区

这意味着报价 Agent 的输出必须与现有模板骨架对齐，而不是自由格式文本。

---

## 3. 核心诉求

本项目的核心诉求是：

> 将服贸人员的报价流程由 Agent 实现，并输出可直接映射到现有报价模板的标准结构化 `QuoteDocument JSON`。

智能报价 Agent 需要完成以下工作：

1. 接收智能评估 Agent 输出的评估单
2. 标准化评估单中的报价相关信息
3. 判断可报价项、待确认项与排除项
4. 结合历史报价数据库进行参考与校验
5. 生成符合模板约束的报价项结构
6. 支持单方案或多方案报价
7. 输出表尾 Summary、Remark 与 Service Payment Terms
8. 最终输出 `QuoteDocument JSON`

补充说明：在当前版本中，系统已经开始支持“报价草案反馈飞轮”能力，即：

1. 用户对草案的修改意见可结构化采集
2. 反馈可写入本地 memory
3. memory 可被后续报价检索消费
4. 高频反馈可聚合为 rule candidate，并经审核后升级为 approved rule

---

## 4. 设计范围

## 4.1 本期纳入范围
本期智能报价 Agent 聚焦于“从评估单到报价文档 JSON”的核心能力，包括：

- 评估单解析与标准化
- 报价可行性判断
- 历史报价参考
- 报价项生成
- 多方案组织
- 表尾结果生成
- 审核提示与追溯信息输出
- 标准 `QuoteDocument JSON` 输出

补充说明：当前仓库实现还额外包含以下反馈飞轮相关能力：

- `quote_feedback_capture_skill`
- `quote_feedback_reference_skill`
- `quote_feedback_rule_review_skill`
- `.opencode/memory/` 本地记忆目录

## 4.2 本期不纳入范围
以下内容不属于本期核心范围：

- 从原始客户邮件直接生成完整报价
- 自动对外发送客户邮件
- 自动发起审批流
- 自动调用采购系统实时询价
- 自动输出最终 Word 文件
- 成单后全链路自动跟单

这些能力可作为后续扩展，但不应混入本期 Skill 核心设计。

补充说明：当前仓库实现已包含可选的 `quote_pdf_render_skill`，可在 `QuoteDocument JSON` 生成后继续输出 HTML/PDF 文件。该能力属于后处理渲染层，不改变前述“报价核心链路以 QuoteDocument 为主产物”的设计边界。

---

## 5. 设计原则

## 5.1 Skill 数量适中，避免过度拆分
Skill 设计应遵循“高内聚、低耦合”的原则。  
若拆分过细，会导致：

- 链路过长
- 上下文传递复杂
- 错误定位困难
- 维护成本高

因此，本方案采用**少量核心 Skill + 一个编排层**的结构。

## 5.2 输出优先围绕模板，而不是围绕文本
报价 Agent 的最终产物必须优先服务于：

- 报价模板渲染
- 内部审核
- 前端展示
- 导出为 Excel / Word / PDF
- 数据归档和追溯

因此输出模型必须优先是**结构化文档模型**，而不是自由文本。

## 5.3 输入输出统一 JSON 化
所有 Skill 之间统一使用 JSON 作为输入输出协议，以支持：

- 日志记录
- 数据持久化
- 模板渲染
- 调试测试
- 前后端对接

## 5.4 规则计算与语言生成分离
### 适合规则引擎 / 程序计算的部分
- 工时费计算
- 系数加价
- 附加费计算
- 折扣计算
- 汇总计算
- 状态归类
- 金额格式化

### 适合 Agent / LLM 的部分
- 评估单理解
- 历史报价模式归纳
- 待确认项识别
- remark / exclusion / tbc 文案生成
- 风险与审核提示生成

## 5.5 骨架固定，内容动态
`QuoteDocument` 的顶层结构、表头结构、明细列结构和表尾结构固定。  
具体的：

- quotation option 数量
- section 数量
- group 数量
- line 数量
- remark 条数

则根据实际报价动态变化。

## 5.6 不确定项必须显式输出
系统不得在信息不完整时“默认补全”。  
对于待确认、按实际、额外收费、客户侧提供等情况，必须结构化表达。

---

## 6. 总体架构

```text
智能评估单
  +
历史报价数据库
  +
反馈记忆 / approved rules
  +
报价规则配置
  +
必要人工补充信息
    ↓
智能报价 Agent
    ↓
QuoteDocument JSON
    ↓
报价模板渲染器（HTML / Excel / Word / PDF）
    ↓
正式报价单
```

---

## 7. 固定报价模板约束

本项目必须遵循固定报价模板约束。

---

## 7.1 固定表头字段

表头必须始终存在以下字段，即使值为空也必须保留：

1. `Currency`
2. `Vessel Name`
3. `Date`
4. `IMO No.`
5. `Vessel Type`
6. `Customer Name`
7. `Service Port`
8. `Attention`
9. `WK Offer No.`
10. `Your Ref No.`
11. `Quotation Validity`
12. `PO No.`
13. `PIC of WinKong`

### 推荐 JSON 结构
```json
{
  "header": {
    "currency": "",
    "vessel_name": "",
    "date": "",
    "imo_no": "",
    "vessel_type": "",
    "customer_name": "",
    "service_port": "",
    "attention": "",
    "wk_offer_no": "",
    "your_ref_no": "",
    "quotation_validity": "",
    "po_no": "",
    "pic_of_winkong": ""
  }
}
```

---

## 7.2 固定中间报价列

报价明细表固定包含以下列：

1. `Item`
2. `Description`
3. `Unit Price`
4. `Unit`
5. `Q'ty`
6. `Discount`
7. `Amount`

### 推荐 JSON 结构
```json
{
  "table_schema": {
    "columns": [
      { "key": "item", "label": "Item" },
      { "key": "description", "label": "Description" },
      { "key": "unit_price", "label": "Unit Price" },
      { "key": "unit", "label": "Unit" },
      { "key": "qty", "label": "Q'ty" },
      { "key": "discount", "label": "Discount" },
      { "key": "amount", "label": "Amount" }
    ]
  }
}
```

---

## 7.3 固定表尾字段

表尾必须包含以下三个区域：

1. `Summary`
2. `Remark`
3. `Service Payment Terms`

其中 `Summary` 中必须包含四个字段：

- `Service Charge`
- `Spare Parts Fee`
- `Other`
- `Total`

### 推荐 JSON 结构
```json
{
  "footer": {
    "summary": {
      "service_charge": {},
      "spare_parts_fee": {},
      "other": {},
      "total": {}
    },
    "remark": {
      "title": "Remark",
      "items": []
    },
    "service_payment_terms": {
      "title": "Service Payment Terms",
      "content": ""
    }
  }
}
```

---

## 8. 输出模型：QuoteDocument

## 8.1 顶层结构

```json
{
  "document_type": "quotation",
  "document_version": "1.1",
  "header": {},
  "table_schema": {},
  "quotation_options": [],
  "footer": {},
  "review_result": {},
  "trace": {}
}
```

---

## 8.2 顶层字段说明

### `document_type`
固定为 `quotation`。

### `document_version`
当前文档结构版本号。

### `header`
固定表头信息。

### `table_schema`
固定表格列定义。

### `quotation_options`
正文报价内容，支持单方案或多方案。

### `footer`
固定表尾结构，包含 Summary / Remark / Service Payment Terms。

### `review_result`
内部审核信息。

### `trace`
定价依据与追溯信息。

---

## 9. 多方案报价模型

实际报价中可能存在：

- 单方案报价
- 多方案报价（如 Option A / Option B）

因此，报价模型必须支持 `quotation_options`。

---

## 9.1 单方案报价
若只有一个方案，则：

- `quotation_options` 数组长度为 1
- `footer.summary` 默认等于该方案 summary

---

## 9.2 多方案报价
若存在多个方案，则：

- 每个 option 必须有独立的 `summary`
- `footer.summary` 不得简单将各方案金额相加
- `footer.summary` 应按以下策略之一生成：
  1. 取默认推荐方案 summary
  2. 若尚未确定推荐方案，则显示 `Refer to selected option` / `Pending`

---

## 9.3 Option 结构

```json
{
  "option_id": "",
  "title": "",
  "sections": [],
  "summary": {},
  "remarks": []
}
```

### 字段说明
- `option_id`：方案唯一标识
- `title`：方案标题
- `sections`：方案正文内容
- `summary`：方案级汇总
- `remarks`：方案专属备注

---

## 10. 文档正文结构

正文采用分层结构：

```text
quotation_options
  └─ sections
      └─ groups
          └─ lines
```

---

## 10.1 Section
Section 用于表达正文中的一级逻辑区域。

```json
{
  "section_id": "",
  "section_type": "service | spare_parts | other",
  "title": "",
  "groups": []
}
```

---

## 10.2 Group
Group 用于表达 section 下的逻辑分组，例如：

- 某个设备模块
- 某个服务子项
- 某个费用模块

```json
{
  "group_id": "",
  "group_no": "",
  "title": "",
  "description": "",
  "lines": []
}
```

### 注意
当前版本**不建议引入 group summary**。  
summary 仅保留在：

- `quotation_options[].summary`
- `footer.summary`

---

## 10.3 Line
Line 是最核心的报价行结构，用于表达：

- 收费项
- 说明项
- 条件项
- 待定项
- 额外收费项
- 技术说明项

### 推荐结构
```json
{
  "line_id": "",
  "item": "",
  "line_no": "",
  "line_type": "",
  "description": "",
  "pricing_mode": "",
  "unit_price": null,
  "unit_price_display": "",
  "unit": "",
  "qty": null,
  "qty_display": "",
  "discount": null,
  "amount": null,
  "amount_display": "",
  "currency": "USD",
  "status": "",
  "basis": "",
  "conditions": [],
  "notes": []
}
```

---

## 11. Line 设计规范

## 11.1 `line_type`
用于表达该行的语义类型，建议支持：

- `priced`
- `included`
- `pending`
- `optional`
- `conditional`
- `extra`
- `note`
- `header`
- `scope_note`
- `technical_note`
- `assumption_note`
- `commercial_note`

---

## 11.2 `pricing_mode`
用于表达该行的计价方式，建议支持：

- `unit_price`
- `lump_sum`
- `included`
- `pending`
- `conditional`
- `text_only`
- `rate_only`
- `rate_as_actual`

---

## 11.3 `status`
用于表达该行当前收费状态，建议支持：

- `chargeable`
- `included`
- `pending`
- `if_needed`
- `extra`
- `as_actual`
- `arranged_by_agent`
- `by_owner`
- `excluded`

---

## 11.4 `discount`
由于模板中已固定存在 `Discount` 列，因此 line 结构中必须支持折扣字段。

### 推荐结构
```json
{
  "discount": {
    "type": "percentage | amount",
    "value": 10,
    "display": "10%"
  }
}
```

### 约束
- 无折扣时为 `null`
- `amount` 字段表示折后金额或最终金额
- 不得将折扣信息仅写在 description 中

---

## 11.5 金额与展示字段
金额类字段建议同时保留：

- 原始值字段
- 展示值字段

例如：

```json
{
  "unit_price": 10000.0,
  "unit_price_display": "10,000.00",
  "amount": 9000.0,
  "amount_display": "9,000.00"
}
```

### 原则
- 原始值字段用于计算、汇总、校验
- 展示字段用于模板渲染
- 金额展示统一为：
  - 千分位
  - 保留两位小数

---

## 12. Summary 设计规范

Summary 需要支持的不仅是数值，还要支持待定、按实际、文本说明等状态。

因此，summary 中每个字段不应简单使用 number，而应使用结构化对象。

---

## 12.1 Summary 字段
固定包含：

- `service_charge`
- `spare_parts_fee`
- `other`
- `total`

---

## 12.2 SummaryValue 推荐结构
```json
{
  "value_type": "amount | status | text",
  "amount": null,
  "display": "",
  "currency": "USD",
  "status": ""
}
```

### 说明
- `value_type = amount`：表示数值金额
- `value_type = status`：表示 Pending / As actual 等状态
- `value_type = text`：表示其他文本

---

## 12.3 双层 Summary 规则

### 方案级 summary
`quotation_options[].summary`  
表示**某个方案自己的汇总结果**。

### 表尾 summary
`footer.summary`  
表示**整份报价单固定模板中的最终表尾汇总区**。

### 规则
- 单方案时，`footer.summary` 默认等于唯一 option 的 summary
- 多方案时，`footer.summary` 取默认推荐方案，或显示 `Refer to selected option` / `Pending`
- 禁止将多个方案 summary 直接相加后写入 footer

---

## 13. Remark 与 Service Payment Terms

## 13.1 Remark
表尾必须有 `Remark` 区域。

### 推荐结构
```json
{
  "remark": {
    "title": "Remark",
    "items": [
      {
        "type": "",
        "text": ""
      }
    ]
  }
}
```

### 建议 remark 类型
- `warranty`
- `compensation`
- `commercial`
- `cost_clause`
- `tax`
- `waiting`
- `safety`
- `exclusion`
- `tbc`
- `payment_term`

---

## 13.2 Service Payment Terms
表尾必须有 `Service Payment Terms` 区域。

### 推荐结构
```json
{
  "service_payment_terms": {
    "title": "Service Payment Terms",
    "content": ""
  }
}
```

---

## 14. 审核与追溯字段

## 14.1 `review_result`
用于内部审核，建议结构如下：

```json
{
  "review_result": {
    "review_flags": [],
    "risk_flags": [],
    "approval_level": ""
  }
}
```

### 字段说明
- `review_flags`：审核提示
- `risk_flags`：风险提示
- `approval_level`：建议审批级别

---

## 14.2 `trace`
用于记录定价依据和引用来源。

```json
{
  "trace": {
    "historical_references": [],
    "pricing_basis": [],
    "rule_versions": []
  }
}
```

---

## 15. Skill 设计

本方案当前已形成 5 个核心报价 Skill + 1 个编排层 + 3 个反馈飞轮 Skill。

---

## 15.1 `quote_request_prepare_skill`

### 目标
将智能评估单与补充上下文转换为统一报价请求对象。

### 输入
```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {}
}
```

### 输出
```json
{
  "quote_request": {},
  "normalization_flags": [],
  "missing_fields": []
}
```

### 核心职责
- 提取报价所需信息
- 标准化服务项
- 标准化服务场景
- 标准化报价输入对象

---

## 15.2 `quote_feasibility_check_skill`

### 目标
判断哪些内容可以报价，哪些必须待确认。

### 输入
```json
{
  "quote_request": {}
}
```

### 输出
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

### 核心职责
- 判断可报价范围
- 识别待确认项
- 识别排除项
- 形成审核提示

---

## 15.3 `historical_quote_reference_skill`

### 目标
从历史报价数据库检索相似案例，并形成报价参考摘要。

### 输入
```json
{
  "quote_request": {},
  "quotable_items": []
}
```

### 输出
```json
{
  "matches": [],
  "reference_summary": {},
  "confidence": 0.0
}
```

### 核心职责
- 检索相似历史报价
- 提供价格带参考
- 提供常见报价项参考
- 提供历史 remark 模式参考

---

## 15.4 `quote_pricing_skill`

### 目标
结合报价请求、可报价范围、历史参考与规则配置，生成正文报价结构与方案级 summary。

### 输入
```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_rules": {}
}
```

### 输出
```json
{
  "quotation_options": []
}
```

### 核心职责
- 生成单方案或多方案报价结构
- 输出 section / group / line
- 输出 line 的状态、折扣与金额
- 输出 option 级 summary
- 对不同方案分别建模

### 特别说明
本 Skill 不只负责“计算金额”，还负责将报价结果映射为固定模板中间表格结构。

---

## 15.5 `quote_review_output_skill`

### 目标
生成最终 `QuoteDocument`，补齐 footer、remark、payment terms、review_result 与 trace。

### 输入
```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

### 输出
```json
{
  "quote_document": {}
}
```

### 核心职责
- 生成固定 header
- 生成固定 table_schema
- 生成 footer.summary
- 生成 footer.remark
- 生成 footer.service_payment_terms
- 输出 review_result
- 输出 trace

### 特别说明
在多方案场景下，本 Skill 必须负责确定 footer.summary 的生成策略。

---

## 15.6 `quote_orchestration_skill`

### 目标
作为智能报价 Agent 的唯一对外 workflow 入口，统一接收整单报价请求并输出最终报价文档。

### 定位

- Agent 做整单报价时，应调用 `quote_orchestration_skill`
- 该 Skill 内部封装现有 Hybrid 编排实现
- `quote_orchestrator` 仅作为内部实现层存在，不再作为对外独立入口暴露

### 推荐流程
```text
quote_orchestration_skill
  └─ 内部调用 Hybrid workflow
      ├─ quote_template_select_skill（可选）
      ├─ quote_request_prepare_skill
      ├─ quote_feedback_reference_skill
      ├─ quote_feasibility_check_skill
      ├─ historical_quote_reference_skill（可选）
      ├─ quote_pricing_skill
      ├─ quote_review_output_skill
      └─ quote_pdf_render_skill（可选）
```

## 15.7 `quote_feedback_capture_skill`

### 目标
将用户对报价草案的修改意见转为结构化反馈事件，并写入本地 memory。

### 当前作用
- 生成 `feedback_event`
- 生成 `preference_candidate`
- 生成 `rule_candidate`
- 写入 `.opencode/memory/`

## 15.8 `quote_feedback_reference_skill`

### 目标
在生成新报价前检索 feedback memory、preference memory 与 approved rules，并输出结构化建议。

### 当前作用
- 输出 `forbidden_patterns`
- 输出 `review_alerts`
- 输出 `applicable_rules`

## 15.9 `quote_feedback_rule_review_skill`

### 目标
审核已达到稳定阈值的 rule candidate，并决定是否写入 approved rules。

### 当前作用
- 读取 `.opencode/memory/rule-candidates/`
- 执行 `approve / reject`
- 写入 `.opencode/memory/approved-rules/`

---

## 16. 定价规则配置建议

报价 Agent 不应把业务规则硬编码到 prompt 中。  
建议将以下规则外置：

### 16.1 费率规则
- 轮机主管费率
- 轮机钳工 / 焊工费率
- 电气主管费率
- 电气助理费率
- 海外费率表

### 16.2 系数规则
- OEM 加价系数
- 替代件加价系数
- 运费系数
- 供船费系数
- 第三方加价系数

### 16.3 附加费用规则
- 食宿
- 交通
- 进港费
- 船厂管理费
- 海事报备费
- 等待费

### 16.4 商务条款模板
- 质保
- 赔偿期限
- waiting 条款
- safety 条款
- payment terms 模板

---

## 17. MVP 范围建议

第一阶段优先落地以下能力：

1. 接收评估单
2. 生成统一报价请求对象
3. 判断可报价范围
4. 检索历史报价参考
5. 输出单方案或多方案报价结构
6. 输出固定 footer 结构
7. 输出标准 `QuoteDocument JSON`

### MVP 纳入 Skill
- `quote_request_prepare_skill`
- `quote_feasibility_check_skill`
- `historical_quote_reference_skill`
- `quote_pricing_skill`
- `quote_review_output_skill`

补充说明：当前实际仓库实现中，反馈飞轮 MVP 也已经落地，包括：

- `quote_feedback_capture_skill`
- `quote_feedback_reference_skill`
- `quote_feedback_rule_review_skill`

补充说明：针对草案纠错流程，当前推荐的结束机制不是由系统自动猜测用户是否满意，而是由用户显式在以下两个动作中二选一：

1. `继续修改`
2. `确认当前版本`

只有当用户明确选择 `确认当前版本` 时，才视为本轮纠错流程结束。

当前实现补充：该机制已经通过 `quote_orchestration_skill` 落地为对话式契约，系统可输出：

1. `draft_status`
2. `user_decision`
3. `user_decision_prompt`

并支持在下一轮输入中接收：

1. `user_decision: "accept"`
2. `user_decision: "revise"`

### MVP 暂不纳入
- 自动发客户邮件
- 自动审批流
- 自动导出正式文件
- 自动成单跟单

---

## 18. 成功标准

若系统达到以下效果，可视为第一阶段成功：

1. 能稳定消费智能评估 Agent 的评估结果
2. 能输出符合固定模板约束的 `QuoteDocument JSON`
3. 能支持单方案和多方案报价
4. 能清晰区分 chargeable / pending / if needed / extra / as actual 等状态
5. 能支持折扣列
6. 能生成固定表头、固定表尾和固定明细列
7. 能生成审核提示和追溯信息
8. 能将输出结果稳定渲染为现有报价单模板

补充说明：若纳入反馈闭环视角，当前版本还应满足：

9. 用户能在 `继续修改 / 确认当前版本` 之间显式决策
10. 系统不会仅凭沉默、导出 PDF 或修改次数减少来猜测用户已经满意

---

## 19. 结论

本设计方案的核心不再是“生成一个抽象报价草案”，而是：

- **以固定模板为骨架**
- **以多方案与动态报价项为内容**
- **以 JSON 为标准输出**
- **以规则计算与 Agent 理解协同实现**

在已有**智能评估 Agent**和**历史报价数据库**的基础上，推荐优先建设“评估单 → QuoteDocument JSON”这一段核心能力，并围绕固定模板逐步落地智能报价 Agent。

---

## 附录 A：推荐 Skill 命名清单

- `quote_request_prepare_skill`
- `quote_feasibility_check_skill`
- `historical_quote_reference_skill`
- `quote_pricing_skill`
- `quote_review_output_skill`
- `quote_orchestration_skill`

---

## 附录 B：推荐最小输出物清单

本系统建议至少输出以下结构化结果：

1. `quote_request`
2. `feasibility_result`
3. `historical_reference`
4. `quotation_options`
5. `quote_document`
6. `review_result`
7. `trace`

---

## 附录 C：推荐实施顺序

### 第一阶段
- 定义 QuoteDocument JSON Schema
- 定义固定模板字段与列约束
- 接通评估单输入
- 打通历史报价检索
- 完成报价方案输出
- 完成 footer 输出

### 第二阶段
- 增强价格解释能力
- 增强折扣策略
- 增强审核策略
- 增加模板渲染器

### 第三阶段
- 接入审批流
- 接入导出能力
- 接入邮件发送
- 接入成单跟单流程
