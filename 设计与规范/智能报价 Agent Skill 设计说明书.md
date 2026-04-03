# 智能报价 Agent Skill 设计说明书（V1）

## 1. 文档目标

本文档用于定义“服务贸易报价流程”中可抽离为 Agent Skills 的能力边界、输入输出、编排流程、规则依赖与实施方案，用于支持以下目标：

- 将人工报价经验沉淀为可复用的 Agent Skills
- 基于**智能评估报告**自动生成报价草案
- 结合**历史报价数据库**提供数据依据与相似案例参考
- 支持**一份评估单对应多项服务**的组合报价场景
- 输出可审核、可追溯、可逐步自动化的智能报价能力

---

## 2. 背景与现状

当前业务已具备以下基础能力：

### 2.1 智能评估系统
输入需求单（包含服务类型、服务归口、设备信息等基础信息），输出智能评估报告。评估报告通常包含：

- 船舶基础信息
- 多个需求项的服务评估结果
- 各需求项的施工任务
- 工种 / 职级 / 人数 / 单人工时
- 风险提示
- 工具 / 耗材 / 专用工具建议
- 设备 / 备件需求
- 审核重点与待确认事项
- 汇总工时、人数等信息

### 2.2 历史报价数据
历史报价单数据已完成结构化入库，可用于：

- 相似报价案例召回
- 常见报价项参考
- 历史价格区间分析
- 附加费用习惯分析
- remark 模板建议
- 成交 / 未成交经验沉淀

### 2.3 业务规则来源
报价规则来自现有培训手册与业务经验，主要包括：

- 备件、服务、服务+备件的处理方式
- 轮机 / 电气 / 第三方的不同路径
- 国内 / 新加坡 / 巴拿马等区域价目规则
- 差旅食宿、进港费、报备费、管理费等附加费用规则
- warranty、compensation、waiting、safety 等商务条款
- 折扣期限与审核要求

---

## 3. 产品定位

本项目建议定位为：

# 智能报价 Agent Skill Center

其核心能力为：

1. 接收智能评估报告  
2. 解析并标准化评估数据  
3. 检索历史报价数据库中的相似案例  
4. 结合报价规则生成多服务组合报价草案  
5. 自动标记待确认项、风险项、审核项  
6. 输出报价明细、remark、审核建议和客户邮件草稿  

---

## 4. 设计原则

### 4.1 LLM 与规则引擎分工明确
- **LLM 负责**：
  - 解析评估报告
  - 理解服务项与风险信息
  - 生成报价说明、remark、邮件草稿
  - 辅助识别漏项与异常

- **规则引擎负责**：
  - 费率计算
  - 系数加价
  - 附加费计算
  - 审批阈值
  - 折扣权限
  - 地区价目规则
  - 共享费用合并逻辑

### 4.2 以评估单为主输入
报价 Agent 的主输入不再直接依赖原始客户邮件，而是依赖：

- 智能评估报告
- 历史报价数据
- 报价规则配置
- 必要的人工确认信息

### 4.3 支持多项服务联合报价
一份评估报告可能包含多个需求项，必须支持：

- 单项服务独立生成报价行
- 整单共享费用识别与合并
- 多项服务统一输出报价草案

### 4.4 待确认项必须显式输出
系统不能“假设完整”，必须明确指出：

- 当前可报价部分
- 需补充确认部分
- 仅可作为备注或 exclusion 的部分

### 4.5 人工审核不可省略
初期设计中，智能报价系统输出的是：

- **报价草案**
- **审核建议**
- **风险提示**

而不是跳过人工直接对外发送。

---

## 5. 总体架构

## 5.1 三层架构

### 第一层：需求理解层
输入来源：
- 客户询价邮件
- 需求单
- 手工录入信息

输出：
- 结构化需求上下文

> 注：此层不是本阶段核心，但保留扩展接口。

### 第二层：服务评估层
输入：
- 结构化需求

输出：
- 智能评估报告

> 当前该层已有现成系统，不在本次重做范围内。

### 第三层：智能报价层
输入：
- 智能评估报告
- 历史报价数据库结果
- 报价规则配置
- 人工补充确认信息

输出：
- 报价草案
- 报价明细
- remark
- 风险与审核提示
- 客户邮件草稿

---

## 6. 核心业务流程

```text
客户询价 / 需求单
    ↓
智能评估系统
    ↓
assessment_parse_skill
    ↓
assessment_normalize_skill
    ↓
quote_gap_check_skill
    ↓
historical_quote_retrieval_skill
    ↓
quote_line_generation_skill
    ↓
additional_cost_skill
    ↓
pricing_strategy_skill
    ↓
multi_service_quote_aggregation_skill
    ↓
remark_generate_skill
    ↓
quote_review_check_skill
    ↓
quote_document_generation_skill
    ↓
customer_email_reply_skill
```

---

## 7. 核心数据对象设计

## 7.1 AssessmentReport（评估报告对象）

```json
{
  "vessel": {
    "name": "",
    "hull_no": "",
    "shipyard": "",
    "delivery_date": "",
    "vessel_type": "",
    "main_engine_model": "",
    "running_hours": 0,
    "drydock_window": [],
    "region": ""
  },
  "service_items": [
    {
      "request_id": "",
      "department": "",
      "service_description": "",
      "service_type": "",
      "service_location": "",
      "equipment_name": "",
      "equipment_model": "",
      "maker": "",
      "quantity": 0,
      "unit": "",
      "remark": "",
      "scope_detail": "",
      "tasks": [
        {
          "content": "",
          "trade": "",
          "grade": "",
          "headcount": 0,
          "hours_per_person": 0
        }
      ],
      "summary": {
        "is_riding": false,
        "total_hours": 0,
        "total_people": 0
      },
      "tools": [],
      "materials": [],
      "special_tools": [],
      "spare_parts_tbc": [],
      "risks": [],
      "review_focus": []
    }
  ],
  "global_tbc_items": [],
  "report_meta": {
    "generated_at": "",
    "version": ""
  }
}
```

---

## 7.2 HistoricalQuoteMatch（历史报价匹配结果）

```json
{
  "matched_quotes": [
    {
      "quote_id": "",
      "similarity": 0.0,
      "service_item": "",
      "service_type": "",
      "department": "",
      "location": "",
      "currency": "",
      "service_amount": 0,
      "parts_amount": 0,
      "travel_amount": 0,
      "other_amount": 0,
      "remarks": [],
      "won_or_lost": "",
      "quote_date": ""
    }
  ],
  "pricing_benchmark": {
    "service_amount_min": 0,
    "service_amount_median": 0,
    "service_amount_max": 0
  },
  "common_additional_costs": [],
  "common_remarks": [],
  "confidence": 0.0
}
```

---

## 7.3 QuoteDraft（报价草案）

```json
{
  "quote_header": {
    "quote_no": "",
    "customer_name": "",
    "vessel_name": "",
    "currency": "USD",
    "location": "",
    "berth_or_anchorage": "",
    "quote_basis_note": ""
  },
  "line_groups": [
    {
      "request_id": "",
      "title": "",
      "lines": [
        {
          "category": "service | parts | travel | lodging | port_fee | management_fee | other",
          "description": "",
          "qty": 0,
          "unit": "",
          "unit_price": 0,
          "amount": 0,
          "basis": "",
          "is_shared_cost": false
        }
      ]
    }
  ],
  "subtotals": {
    "service_subtotal": 0,
    "parts_subtotal": 0,
    "shared_cost_subtotal": 0,
    "grand_total": 0
  },
  "remarks": [],
  "exclusions": [],
  "tbc_items": [],
  "review_flags": [],
  "approval_level": "",
  "email_draft": ""
}
```

---

## 8. Skill 清单设计

## 8.1 assessment_parse_skill

### 目标
将评估报告文本解析为结构化对象。

### 输入
- 智能评估报告原文（Markdown / 富文本 / JSON）

### 输出
- `AssessmentReport`

### 关键职责
- 抽取船舶基础信息
- 识别每一个需求项
- 提取任务级施工数据
- 提取风险、工具、耗材、专用工具、备件需求
- 提取全局待确认事项与汇总信息

### 注意事项
- 一份评估报告可包含多个服务项
- 输出需保留 request_id 或生成稳定索引

---

## 8.2 assessment_normalize_skill

### 目标
对评估报告中的数据进行标准化、一致性检查与报价优先级判断。

### 输入
- `AssessmentReport`

### 输出
```json
{
  "normalized_items": [],
  "consistency_flags": [],
  "pricing_use_recommendation": {
    "use_task_level_data_first": true,
    "require_manual_confirmation": false
  }
}
```

### 关键职责
- 检查任务级 headcount 与 summary 总人数是否冲突
- 检查任务级工时与汇总工时是否冲突
- 标准化工种名称、职级名称
- 标准化地点类型（港口 / 船厂 / 随航）
- 判断后续报价优先使用哪层数据（任务级 / 汇总级）

### 典型问题
- 任务表显示 1+7 人，但汇总显示 2 人
- “校验”服务描述实际更接近 overhaul
- 是否航修与干坞场景冲突

---

## 8.3 quote_gap_check_skill

### 目标
识别当前评估数据下，哪些内容可直接报价，哪些必须待确认。

### 输入
- 标准化后的评估数据
- 基础客户上下文

### 输出
```json
{
  "quotable_now": true,
  "quote_mode": "full | partial_with_tbc | not_ready",
  "tbc_items": [],
  "must_confirm_before_submission": [],
  "recommended_customer_questions": []
}
```

### 关键职责
- 判断能否先报服务费
- 判断备件是否需单独待确认
- 判断专用工具、耗材、船厂管理费等是否缺依据
- 判断币种、码头/锚地等商务信息是否缺失

---

## 8.4 historical_quote_retrieval_skill

### 目标
检索历史报价数据库中的相似案例。

### 输入
- 船型
- 主机型号
- 设备名称
- 服务类型
- 服务归口
- 区域
- 航修/厂修
- 多服务组合信息

### 输出
- `HistoricalQuoteMatch`

### 检索维度建议
- 设备名称 / 型号
- 服务描述 / 服务类型
- 主机型号
- 船舶类型
- 作业区域
- 地点类型
- 是否多服务组合
- 报价时间范围
- 是否成交

### 检索结果用途
- 价格带参考
- 常见 line items 参考
- 附加费用参考
- remark 参考
- 异常低价 / 高价对比

---

## 8.5 historical_pattern_summary_skill

### 目标
将多条相似历史报价归纳为对本次报价有帮助的模式摘要。

### 输入
- 历史相似报价列表

### 输出
```json
{
  "common_line_items": [],
  "common_exclusions": [],
  "common_remarks": [],
  "usual_price_band": {},
  "pricing_pattern_notes": []
}
```

### 作用
- 帮助报价 Agent 不只是“看列表”，而是“总结规律”
- 形成可用于解释的定价依据

---

## 8.6 quote_line_generation_skill

### 目标
针对每个服务项生成服务类报价行。

### 输入
- 标准化评估服务项
- 历史报价模式摘要
- 费率规则

### 输出
```json
{
  "quote_line_groups": [
    {
      "request_id": "",
      "title": "",
      "lines": []
    }
  ]
}
```

### 关键职责
- 将任务级工种、人数、工时映射为 labor charge
- 按轮机 / 电气使用不同费率规则
- 对每个需求项独立生成 line group
- 标记依据来源：
  - assessment_task
  - assessment_summary
  - historical_reference
  - manual_rule

### 典型映射规则
- 轮机主管：55 USD/人/小时
- 轮机钳工 / 焊工：35 USD/人/小时
- 电气主管：60 USD/人/小时
- 电气助理：40 USD/人/小时
- 海外区域费率从价目表读取，不写死

---

## 8.7 parts_pricing_skill

### 目标
对明确的备件项目生成备件报价行。

### 输入
- 备件底价 / 采购价
- 备件归属
- 是否 OEM
- 是否替代件
- 尺寸重量
- 供船费依据
- 历史备件报价参考

### 输出
```json
{
  "parts_lines": [],
  "warnings": []
}
```

### 规则
- OEM 一般加价 1.15 ~ 1.35
- 替代件一般约 1.5
- 运费若不含，按预估再乘 1.3 ~ 1.5
- 供船费按代理价乘 1.35 ~ 1.5

### 注意
若评估报告中备件为“待确认”，则不直接生成正式金额，可输出：
- excluded
- to be confirmed separately

---

## 8.8 additional_cost_skill

### 目标
生成附加费用项。

### 输入
- 服务地点
- 是否航修 / 厂修 / 随航
- 区域
- 人数
- 天数 / 工时
- 是否涉及动火 / 报备
- 船厂 / 码头条件
- 历史附加费参考

### 输出
```json
{
  "additional_lines": [],
  "shared_cost_candidates": [],
  "risk_notes": []
}
```

### 费用范围
- 交通费
- 食宿费
- 进港费
- 进厂 / 安全培训费
- 海事报备费
- 船厂管理费
- 随航上下船费用

### 典型规则
- 交通：票价 * 1.3 ~ 1.35
- 食宿：40 ~ 50 USD/人/天
- 一天内航修一般无需收食宿
- 自办码头进港费 100 ~ 200 USD
- 代理办理按代理费 * 1.3 ~ 1.5
- 厂修进厂按实际收费 * 1.15 ~ 1.3
- 海事报备费 100 ~ 200 USD 或第三方报价基础调整

---

## 8.9 multi_service_quote_aggregation_skill

### 目标
将多项服务报价合并为整单报价。

### 输入
- 各需求项的报价 line groups
- 附加费用项
- 共享费用候选项

### 输出
```json
{
  "merged_quote": {},
  "deduped_shared_costs": [],
  "allocation_notes": []
}
```

### 关键职责
- 识别共享成本：
  - 交通
  - 食宿
  - 进港费
  - 安全培训费
  - 船厂管理费（视场景）
- 避免重复收费
- 保留服务项分项列示
- 输出整单 subtotal 与 grand total

### 业务原则
- 同船、同地点、同时间窗口的多服务项通常共享一部分附加费
- 服务费按项列示
- 共享费用可单独列一组，避免客户理解歧义

---

## 8.10 pricing_strategy_skill

### 目标
基于历史报价、风险、客户情况与业务策略，给出本次报价策略建议。

### 输入
- 当前成本估算
- 历史价格区间
- 风险等级
- 紧急程度
- 客户类型
- 是否重要客户
- 是否首单
- 是否必须提高赢单概率

### 输出
```json
{
  "strategy": "conservative | standard | competitive | premium_risk",
  "recommended_markup_adjustment": 1.0,
  "discount_headroom": 0.0,
  "reason": []
}
```

### 作用
- 决定报价更偏稳健还是更偏竞争
- 给出是否留折扣空间的建议
- 给出偏离历史中位数的原因解释

---

## 8.11 remark_generate_skill

### 目标
自动生成报价 remark、exclusions 与 TBC 说明。

### 输入
- 报价草案
- 风险信息
- 待确认项
- 业务规则模板

### 输出
```json
{
  "remarks": [],
  "exclusions": [],
  "tbc_statements": []
}
```

### remark 来源
- 备件 warranty
- 服务 warranty（一般 6 个月）
- 检查 / 排故无质保
- compensation 条款
- waiting 条款
- safety 条款
- 备件归属待确认说明
- 基于当前信息报价的限制说明

### 示例
- Service warranty: 6 months from completion date.
- Inspection and troubleshooting items are excluded from warranty.
- Spare parts are excluded and shall be quoted separately upon final confirmation.
- Waiting time caused by vessel delay shall be settled separately.

---

## 8.12 quote_review_check_skill

### 目标
在人工审核前自动检查报价完整性与合规性。

### 输入
- 完整报价草案

### 输出
```json
{
  "passed": true,
  "review_flags": [],
  "approval_level": "self | team_leader | manager | minister",
  "risk_level": "low | medium | high"
}
```

### 检查项
- 币种是否明确
- 码头 / 锚地基准是否明确
- 工作内容是否详细
- 是否存在一句话报价
- 是否缺 warranty
- 是否缺 compensation
- 是否缺 exclusions / TBC
- 是否遗漏交通 / 食宿 / 港杂 / 管理费 / 报备费
- 是否存在与评估报告冲突的数据
- 是否明显偏离历史报价区间
- 是否超出折扣权限

---

## 8.13 profit_guard_skill

### 目标
识别异常低利润报价。

### 输入
- 报价金额
- 估算成本
- 历史利润率参考
- 服务人工收益率标准

### 输出
```json
{
  "margin_status": "healthy | low | abnormal",
  "alerts": [],
  "approval_required": false
}
```

### 规则参考
- 轮机 / 电气人工收益率可对照历史正常区间
- 第三方施工若利润率 < 20%，视为异常提醒

---

## 8.14 quote_document_generation_skill

### 目标
将结构化报价草案生成为标准报价单文档内容。

### 输入
- `QuoteDraft`

### 输出
- Markdown / HTML / PDF 模板渲染数据
- line items
- remarks
- exclusions
- subtotal / total

### 要求
- 支持分项展示多需求项
- 支持共享费用单列
- 支持后续导出为正式报价单格式

---

## 8.15 customer_email_reply_skill

### 目标
生成客户邮件草稿。

### 输入
- 报价结果
- 客户名称
- 船舶名称
- 当前阶段（收悉 / 补资料 / 发报价 / 跟进）

### 输出
```json
{
  "subject": "",
  "body": ""
}
```

### 邮件类型
- 收悉处理中
- 补资料
- 正式发送报价
- 报价后跟进
- 说明部分项目待确认

---

## 9. 评估单到报价单字段映射

| 评估字段 | 报价用途 | 处理规则 |
|---|---|---|
| 业务归口 | 决定费率体系 | 轮机 / 电气使用不同费率 |
| 服务描述 | 生成报价项标题 | 可结合历史案例优化描述 |
| 服务类型 | 决定报价方式 | 校验 / 大修 / 检查 / 调试等 |
| 服务地点 | 决定附加费用 | 港口 / 船厂 / 随航 |
| 所属设备名称 | 相似报价检索 | 作为关键匹配字段 |
| 设备型号 / 厂家 | 相似案例筛选 | 提高相似度精度 |
| 任务-工种 | 生成 labor charge | 映射到费率表 |
| 任务-人数 | 计算工时量 | 人数 × 单人工时 |
| 任务-单人工时 | 计算人工费 | 优先使用任务级数据 |
| 风险提示 | remark / 审核提示 | 高风险触发人工复核 |
| 工具 / 耗材 / 专用工具 | 是否纳入报价 | 不明确时列入 TBC / exclusion |
| 备件需求 | 备件报价或排除项 | 若未确认归属，先不正式计价 |
| 是否航修 | 附加费判定 | 进港、报备、食宿等 |
| 汇总工时 / 人数 | 二级参考 | 与任务级冲突时降级使用 |

---

## 10. 多服务组合报价规则

## 10.1 基本原则
一份评估单可包含多个服务项，报价时需要：

- 保持每项服务清晰分项
- 对共享费用进行合并
- 对待确认项统一管理
- 对整单输出一个总金额

## 10.2 建议展示结构
### 第一部分：服务项报价
- 服务项 1：HCU 系统大修
- 服务项 2：MPC 系统检查
- 服务项 3：其他

### 第二部分：共享费用
- Transportation
- Accommodation
- Port entry / Yard entry
- Safety / filing related fees

### 第三部分：备件
- Included parts
- Excluded parts
- To be confirmed separately

### 第四部分：remark / exclusions / TBC

## 10.3 共享费用规则
以下费用通常应考虑整单共享而非按项重复：

- 交通
- 食宿
- 进港费
- 安全培训费
- 报备费
- 船厂管理费（视收费方式）

## 10.4 不共享费用
以下费用通常按项计：

- 各服务项人工费
- 各服务项专属耗材
- 各服务项专属备件
- 某项特定测试 / 调试 / 校验费

---

## 11. 报价规则配置建议

## 11.1 费率规则
```json
{
  "domestic_engine": {
    "supervisor": 55,
    "fitter_welder": 35
  },
  "domestic_electrical": {
    "supervisor": 60,
    "assistant": 40
  }
}
```

## 11.2 系数规则
```json
{
  "oem_markup_range": [1.15, 1.35],
  "alternative_markup_default": 1.5,
  "freight_markup_range": [1.3, 1.5],
  "delivery_markup_range": [1.35, 1.5],
  "third_party_markup_range": [1.35, 1.5]
}
```

## 11.3 食宿 / 附加费用规则
```json
{
  "meal_hotel_per_day_range": [40, 50],
  "self_handled_port_entry_range": [100, 200],
  "maritime_filing_range": [100, 200]
}
```

## 11.4 商务条款模板
```json
{
  "service_warranty_months": 6,
  "inspection_warranty": "none",
  "max_compensation_multiple": 5,
  "waiting_fee_range": [300, 500]
}
```

---

## 12. 风险与审核机制

## 12.1 风险分类
### 业务风险
- 施工范围不完整
- 备件归属不明
- 工时估算置信度低
- 第三方价格不稳定

### 商务风险
- 币种缺失
- 锚地 / 码头基准不明确
- 报价过低
- 等待条款未写明

### 执行风险
- 动火 / 受限空间审批
- 船厂交叉作业
- 船期窗口不稳定
- 二次登轮可能性

## 12.2 审核升级建议
### 自审
- 标准项目
- 数据完整
- 风险低
- 金额处于常规区间

### 带队师傅 / 组长审核
- 工时估算存在低置信度
- 多服务组合
- 共享费用较复杂

### 经理审核
- 高金额
- 高风险
- 与历史价格偏差较大
- 多个待确认项

### 部长审核
- 重大项目
- 重要客户
- 利润异常
- 涉及重大赔偿风险

---

## 13. 推荐状态机

```text
NEW_ASSESSMENT
PARSED
NORMALIZED
WAITING_CONFIRMATION
HISTORICAL_REFERENCED
DRAFT_PRICED
INTERNAL_REVIEW
REVISE_REQUIRED
READY_TO_SEND
SENT_TO_CUSTOMER
FOLLOWING_UP
CONFIRMED
HANDOFF_TO_ORDER
CLOSED
```

### 状态说明
- `NEW_ASSESSMENT`：收到评估报告
- `PARSED`：已解析
- `NORMALIZED`：已标准化并完成一致性检查
- `WAITING_CONFIRMATION`：存在待确认项
- `HISTORICAL_REFERENCED`：已完成历史案例召回
- `DRAFT_PRICED`：已生成报价草案
- `INTERNAL_REVIEW`：进入内部审核
- `REVISE_REQUIRED`：需要修改
- `READY_TO_SEND`：可对外发送
- `SENT_TO_CUSTOMER`：已发客户
- `FOLLOWING_UP`：待跟进
- `CONFIRMED`：客户确认
- `HANDOFF_TO_ORDER`：移交成单跟单
- `CLOSED`：流程闭环

---

## 14. MVP 范围建议

## 14.1 第一阶段目标
优先实现“从评估报告到报价草案”的核心能力。

### 建议纳入 MVP 的 skills
1. `assessment_parse_skill`
2. `assessment_normalize_skill`
3. `quote_gap_check_skill`
4. `historical_quote_retrieval_skill`
5. `quote_line_generation_skill`
6. `additional_cost_skill`
7. `multi_service_quote_aggregation_skill`
8. `remark_generate_skill`
9. `quote_review_check_skill`
10. `customer_email_reply_skill`

## 14.2 MVP 暂不做
- 自动直连外部采购系统实时报价
- 自动对外发送正式邮件
- 自动审批流闭环
- 全自动生成最终 PDF 并归档
- 成单后全链路跟单自动化

---

## 15. 实施建议

## 15.1 先建统一中间层对象
优先定义统一 JSON Schema，确保：

- 评估系统输出可接入
- 历史报价检索结果可接入
- 各 skill 之间可解耦

## 15.2 历史报价库优先做“召回 + 摘要”
不要一开始就追求复杂推荐模型，先做：

- 条件筛选
- 相似度排序
- Top N 摘要
- 价格带统计

## 15.3 规则配置外置
费率、系数、remark 模板不要写死在 prompt 中，应存于：

- 配置表
- 数据库
- 后台可维护规则中心

## 15.4 保留人工确认节点
对于以下情况，必须要求人工确认：
- 多项服务组合复杂
- 备件归属不明
- 任务人数 / 汇总人数冲突
- 高风险或高金额项目
- 低置信度评估项较多

---

## 16. 成功标准

若系统达到以下效果，可视为第一阶段成功：

1. 能稳定解析一份包含多项服务的评估报告  
2. 能基于评估单自动生成结构化报价草案  
3. 能从历史报价库中召回相似案例并形成参考依据  
4. 能识别待确认项并避免误报完整价格  
5. 能输出清晰的 review flags 与 remark  
6. 能将人工报价准备时间显著缩短  
7. 能帮助新人按统一规则完成报价草案准备  

---

## 17. 后续演进方向

### 17.1 成交反馈闭环
将以下数据回流数据库：
- 最终报价
- 客户议价结果
- 成交 / 未成交
- 未成交原因
- 人工修改点

### 17.2 报价策略优化
基于历史反馈逐步优化：
- 各服务项价格带
- 不同客户的敏感费用项
- 更有效的 remark 模板
- 折扣与成交率关系

### 17.3 全流程自动化
未来可扩展到：
- 报价审批流联动
- 文档自动归档
- 客户邮件自动发送
- 客户确认后自动移交跟单系统

---

## 18. 总结

本设计方案的核心，不是简单将手册改写成 prompt，而是将“经验型报价流程”拆解为：

- 可理解的输入对象
- 可复用的 Agent Skills
- 可配置的业务规则
- 可追溯的审核机制
- 可持续优化的数据闭环

在已有**智能评估系统**与**历史报价数据库**基础上，推荐优先建设“评估单 → 报价草案”这一段核心能力，逐步实现服务贸易报价流程的标准化、半自动化与智能化。

---
## 附录 A：推荐 Skill 命名清单

- `assessment_parse_skill`
- `assessment_normalize_skill`
- `quote_gap_check_skill`
- `historical_quote_retrieval_skill`
- `historical_pattern_summary_skill`
- `quote_line_generation_skill`
- `parts_pricing_skill`
- `additional_cost_skill`
- `multi_service_quote_aggregation_skill`
- `pricing_strategy_skill`
- `remark_generate_skill`
- `quote_review_check_skill`
- `profit_guard_skill`
- `quote_document_generation_skill`
- `customer_email_reply_skill`

---

## 附录 B：推荐输出物

本系统建议至少输出以下结构化结果：

1. 结构化评估数据
2. 历史报价参考摘要
3. 报价 line items
4. 共享费用明细
5. exclusions / TBC 项
6. remark
7. review flags
8. 审核级别建议
9. 客户邮件草稿
