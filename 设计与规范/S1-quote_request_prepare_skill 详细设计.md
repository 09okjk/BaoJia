# `quote_request_prepare_skill` 详细设计

## 1. 文档目的

本文用于细化第一个 Skill：`quote_request_prepare_skill` 的设计，作为后续开发、联调和验收参考。

本设计严格对齐《智能报价 Agent Skill 设计说明书（V2.2）》中的以下约束：

- 第一个 Skill 的目标是“将智能评估单与补充上下文转换为统一报价请求对象”
- 各 Skill 之间统一使用 JSON 作为输入输出协议
- 系统不得在信息不完整时默认补全业务事实
- 后续所有 Skill 都围绕固定模板结构的 `QuoteDocument JSON` 输出服务

---

## 2. Skill 定位

`quote_request_prepare_skill` 是智能报价链路的入口标准化层。

它的职责不是直接报价，而是把上游来源不一、结构不稳定、表述不统一的输入，整理成后续 Skill 可以稳定消费的标准 `quote_request`。

它解决的问题主要有三类：

1. 输入来源多样：评估单、客户补充信息、业务补充信息结构可能不同
2. 字段命名不统一：同一事实可能有多种表述方式
3. 信息完整度不一致：部分字段缺失、模糊、待确认

---

## 3. 目标与非目标

## 3.1 目标

- 接收 `assessment_report`、`customer_context`、`business_context`
- 提取报价所需的核心事实
- 标准化服务项、服务场景、基础上下文
- 输出统一 `quote_request`
- 输出标准化过程中产生的 `normalization_flags`
- 输出后续环节必须关注的 `missing_fields`

## 3.2 非目标

以下内容不属于本 Skill：

- 不判断是否可报价
- 不判断哪些内容应排除
- 不生成 `quotation_options`
- 不计算金额、折扣、汇总
- 不生成 `footer`、`remark`、`service_payment_terms`
- 不生成最终 `QuoteDocument`
- 不默认补全缺失业务事实

这些工作分别由后续 Skill 负责。

---

## 4. 上下游关系

## 4.1 上游输入

本 Skill 接收三类输入：

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {}
}
```

说明：

- `assessment_report`：主输入，来自智能评估 Agent
- `customer_context`：客户邮件、客户补充要求、币种偏好、期望方案等
- `business_context`：内部业务补充，例如区域、历史跟进备注、操作人员补充说明

## 4.2 下游输出

本 Skill 直接服务于：

1. `quote_feasibility_check_skill`
2. `historical_quote_reference_skill`
3. `quote_pricing_skill`

其中：

- `quote_feasibility_check_skill` 依赖 `quote_request` 判断可报价范围
- `historical_quote_reference_skill` 依赖标准化后的服务项和场景做历史检索
- `quote_pricing_skill` 依赖统一后的基础上下文和候选项目建模报价正文

---

## 5. 设计原则

## 5.1 标准化优先，不做业务决策

本 Skill 只做“归一化”和“显式化”，不做“报价判断”。

例如：

- 可以把“船东提供备件”“甲供件”“owner supply”统一为标准状态候选信息
- 不能在本 Skill 直接判断其最终应记为 `by_owner` 还是 `excluded`

## 5.2 保留原始事实，不丢失上下文

标准化后仍应保留关键信息来源，避免后续 Skill 无法追溯原始语义。

## 5.3 缺失信息显式输出

缺什么就记录什么，不做猜测性补全。

## 5.4 为后续固定模板输出做准备

虽然本 Skill 不直接输出 `QuoteDocument`，但其输出字段设计要能平滑映射到后续的：

- 固定表头
- section / group / line 结构
- 方案级 summary
- review / trace 信息

---

## 6. 输入详细设计

## 6.1 输入对象

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {}
}
```

## 6.2 输入字段要求

### `assessment_report`

必须作为主输入存在。

至少应提供以下类型的信息之一：

- 船舶基础信息
- 服务项信息
- 施工内容 / 任务描述
- 工时、人力、工种建议
- 备件需求
- 风险提示
- 待确认事项

若评估单缺少核心报价事实，本 Skill 不负责兜底补造，只负责在 `missing_fields` 中显式标出。

### `customer_context`

可选。用于承接客户侧补充信息，例如：

- 币种要求
- 客户指定工作范围
- 是否需要多方案
- 船期、港口、服务时间补充
- 特殊商务要求

### `business_context`

可选。用于承接内部业务侧补充信息，例如：

- 操作人员备注
- 区域信息
- 需要重点关注的审核点
- 内部建议的服务组织方式

---

## 7. 输出详细设计

## 7.1 输出对象

```json
{
  "quote_request": {},
  "normalization_flags": [],
  "missing_fields": []
}
```

## 7.2 `quote_request` 推荐结构

```json
{
  "request_meta": {
    "request_id": "",
    "source": "assessment_report",
    "prepared_at": "",
    "language": "zh-CN"
  },
  "header_context": {
    "currency": null,
    "vessel_name": null,
    "imo_no": null,
    "vessel_type": null,
    "customer_name": null,
    "service_port": null,
    "service_date": null,
    "attention": null,
    "customer_ref_no": null
  },
  "service_context": {
    "service_category": null,
    "service_mode": null,
    "location_type": null,
    "needs_multi_option": false,
    "option_hints": [],
    "urgency": null
  },
  "candidate_items": [],
  "spare_parts_context": {
    "has_spare_parts": null,
    "spare_parts_supply_mode": null,
    "spare_parts_items": []
  },
  "risk_context": {
    "risks": [],
    "pending_confirmations": [],
    "assumptions": []
  },
  "commercial_context": {
    "preferred_currency": null,
    "pricing_expectation": null,
    "special_terms": []
  },
  "source_refs": {
    "assessment_report_id": null,
    "customer_context_ref": null,
    "business_context_ref": null
  }
}
```

说明：

- `quote_request` 是后续 Skill 的统一输入，不要求直接等同于 `QuoteDocument`
- 但字段设计必须覆盖后续报价、审核、追溯所需的最小事实集合

## 7.3 `normalization_flags` 推荐结构

建议输出为对象数组，而不是纯字符串数组，便于后续审计和调试。

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

典型用途：

- 统一币种表达
- 统一服务类别名称
- 统一地点类型表达
- 合并重复项
- 将自然语言描述归并为标准候选字段

## 7.4 `missing_fields` 推荐结构

建议输出为对象数组。

```json
[
  {
    "field": "header_context.service_port",
    "required_for": ["feasibility_check", "pricing"],
    "severity": "high",
    "reason": "缺少服务地点，影响进港/交通/食宿等费用判断",
    "suggested_source": "customer_context"
  }
]
```

建议严重度：

- `high`：缺失后会直接影响可报价判断或定价
- `medium`：可继续流转，但会影响准确性
- `low`：对报价主结构影响较小

---

## 8. 标准化对象设计

## 8.1 `header_context`

用途：承接未来 `QuoteDocument.header` 所需的基础事实。

设计要求：

- 只保留事实字段，不生成模板显示文案
- 无法确认时填 `null`，并同步记录到 `missing_fields`
- 不在本 Skill 处理日期格式化展示，只保留标准日期值或空值

## 8.2 `service_context`

用途：表达服务场景，用于后续可报价判断和历史检索。

建议字段含义：

- `service_category`：轮机 / 电气 / 第三方 / 综合服务等标准类别
- `service_mode`：航修 / 厂修 / 随航 / 检查 / 故障排查等
- `location_type`：码头 / 锚地 / 船厂 / 航行中等
- `needs_multi_option`：是否存在多方案可能性
- `option_hints`：例如 `Option A` / `Option B` 的线索
- `urgency`：普通 / 紧急等

## 8.3 `candidate_items`

用途：承接后续报价正文的候选服务项。

建议每个候选项结构如下：

```json
{
  "item_id": "",
  "item_type": "service | spare_parts | other",
  "title": "",
  "description": "",
  "work_scope": [],
  "quantity_hint": null,
  "unit_hint": null,
  "labor_hint": [],
  "pricing_clues": [],
  "status_hint": null,
  "source": "assessment_report"
}
```

说明：

- 这里是“候选项”，不是最终 line
- 不要求在本 Skill 中拆到模板级 line 粒度
- 但至少要能支撑后续拆分 section / group / line

## 8.4 `spare_parts_context`

用于显式承接备件相关事实，避免服务与备件信息混杂。

建议关注：

- 是否涉及备件
- 备件由谁提供
- 备件清单是否明确
- 是否仅有需求描述、暂无型号数量

## 8.5 `risk_context`

用于集中表达风险、待确认、假设条件。

其中：

- `risks`：来自评估单或人工补充的风险提示
- `pending_confirmations`：待客户 / 待现场 / 待采购 / 待工程师确认事项
- `assumptions`：当前可继续流转时所依赖的前提假设

---

## 9. 标准化规则

## 9.1 基本规则

1. 统一命名
2. 统一枚举口径
3. 去重但不丢失原始语义
4. 无法确认的事实不强行归类
5. 任何推断都必须可解释

## 9.2 可执行的标准化类型

允许在本 Skill 内执行的标准化包括：

- 币种标准化：如 `USD`、`usd`、`US Dollar` 归一为 `USD`
- 地点表达标准化：如“船厂内”“进厂”归并到统一地点类型
- 服务模式标准化：如“航修”“voyage repair”归并到统一模式
- 文本清洗：去除明显重复、空白、噪声前后缀
- 候选项合并：同一设备、同一工作内容的重复片段合并

## 9.3 明确禁止的动作

本 Skill 禁止：

- 根据经验默认补齐缺失船舶信息
- 根据经验直接生成报价金额
- 将模糊描述擅自改写为确定报价项
- 将待确认项改写为可直接收费项
- 输出任何最终报价结论

---

## 10. 处理流程设计

建议流程如下：

```text
1. 接收原始输入
2. 抽取基础事实
3. 抽取服务相关事实
4. 抽取备件相关事实
5. 抽取风险/待确认/假设信息
6. 统一命名与枚举
7. 识别缺失关键字段
8. 组装 quote_request
9. 输出 normalization_flags 与 missing_fields
```

## 10.1 第一步：输入完整性检查

检查：

- 是否存在 `assessment_report`
- 输入对象是否为 JSON 结构
- 是否存在明显不可解析内容

若主输入缺失，应返回结构化错误，或至少输出高严重度 `missing_fields`。

## 10.2 第二步：基础信息抽取

从输入中优先抽取：

- 船名
- IMO
- 船型
- 客户名称
- 服务地点
- 时间信息
- 币种信息

若多来源冲突，建议优先级：

1. 明确人工补充的 `business_context`
2. 明确客户指定的 `customer_context`
3. `assessment_report`

同时在 `normalization_flags` 中记录冲突处理。

## 10.3 第三步：服务项标准化

将原始评估内容整理为 `candidate_items`。

标准化重点：

- 同类任务合并
- 模块化拆出服务项标题
- 保留工作范围描述
- 保留工程量、工时、人数等线索
- 保留“按实际”“待确认”“如需”等提示

## 10.4 第四步：场景标准化

归纳对定价和可报价判断最关键的场景要素：

- 服务类别
- 服务模式
- 地点类型
- 是否涉及第三方
- 是否涉及备件
- 是否存在多方案可能

## 10.5 第五步：缺失项识别

典型需识别的缺失项包括：

- 币种
- 服务地点
- 服务时间
- 关键工作范围
- 数量或工程量线索
- 备件供货责任
- 是否需要客户确认的关键前提

---

## 11. 缺失信息策略

## 11.1 原则

- 允许继续流转，但必须显式记录
- 不因缺失信息自动停止，除非主输入不可用
- 不在本 Skill 直接向用户追问，由后续 Skill 汇总问题更合适

## 11.2 分类

建议把缺失项分成三类：

1. 表头缺失：影响 `header`
2. 场景缺失：影响可报价判断和定价
3. 项目缺失：影响候选项建模和后续 line 拆分

## 11.3 示例

- 缺 `currency`：可继续，但影响后续金额展示
- 缺 `service_port`：高风险，影响附加费用判断
- 缺关键工作范围：高风险，可能导致只能部分报价

---

## 12. 与后续 Skill 的接口约定

## 12.1 交给 `quote_feasibility_check_skill`

重点提供：

- 标准化后的 `candidate_items`
- `risk_context.pending_confirmations`
- `missing_fields`
- `service_context`

## 12.2 交给 `historical_quote_reference_skill`

重点提供：

- 标准化后的服务类别
- 工作范围摘要
- 船型 / 服务地点 / 服务模式
- 候选项标题与描述

## 12.3 交给 `quote_pricing_skill`

重点提供：

- `header_context`
- `service_context`
- `candidate_items`
- `spare_parts_context`
- `commercial_context`

---

## 13. 异常与错误处理

## 13.1 可恢复问题

例如：

- 部分字段缺失
- 文本描述较模糊
- 同一字段存在多个候选值

处理方式：

- 保留可解析内容
- 记录 `normalization_flags`
- 输出 `missing_fields`

## 13.2 不可恢复问题

例如：

- 缺失 `assessment_report`
- 输入不是有效 JSON 对象
- 主体内容为空且无任何可抽取事实

处理方式：

- 返回结构化失败结果，或至少输出高严重度缺失并停止进入正式报价链路

---

## 14. 示例

## 14.1 示例输入

```json
{
  "assessment_report": {
    "vessel_name": "MV EXAMPLE",
    "imo_no": "1234567",
    "customer_name": "ABC Shipping",
    "service_port": "Zhapu Port, China",
    "service_items": [
      {
        "title": "AE-1 crankshaft trueness checks in place",
        "details": [
          "Working time abt 15 hours",
          "2pcs M/B lower bearing remove",
          "Crankshaft run-out check by magnetic gauge"
        ]
      }
    ],
    "pending_items": [
      "Whether spare parts are owner supply"
    ]
  },
  "customer_context": {
    "currency": "USD"
  },
  "business_context": {
    "service_mode": "voyage repair"
  }
}
```

## 14.2 示例输出

```json
{
  "quote_request": {
    "request_meta": {
      "request_id": "qr-0001",
      "source": "assessment_report",
      "prepared_at": "2026-04-09T10:00:00Z",
      "language": "zh-CN"
    },
    "header_context": {
      "currency": "USD",
      "vessel_name": "MV EXAMPLE",
      "imo_no": "1234567",
      "vessel_type": null,
      "customer_name": "ABC Shipping",
      "service_port": "Zhapu Port, China",
      "service_date": null,
      "attention": null,
      "customer_ref_no": null
    },
    "service_context": {
      "service_category": "service",
      "service_mode": "voyage_repair",
      "location_type": "port",
      "needs_multi_option": false,
      "option_hints": [],
      "urgency": null
    },
    "candidate_items": [
      {
        "item_id": "svc-1",
        "item_type": "service",
        "title": "AE-1 crankshaft trueness checks in place",
        "description": "Working time abt 15 hours",
        "work_scope": [
          "2pcs M/B lower bearing remove",
          "Crankshaft run-out check by magnetic gauge"
        ],
        "quantity_hint": null,
        "unit_hint": null,
        "labor_hint": [],
        "pricing_clues": [],
        "status_hint": null,
        "source": "assessment_report"
      }
    ],
    "spare_parts_context": {
      "has_spare_parts": null,
      "spare_parts_supply_mode": null,
      "spare_parts_items": []
    },
    "risk_context": {
      "risks": [],
      "pending_confirmations": [
        "Whether spare parts are owner supply"
      ],
      "assumptions": []
    },
    "commercial_context": {
      "preferred_currency": "USD",
      "pricing_expectation": null,
      "special_terms": []
    },
    "source_refs": {
      "assessment_report_id": null,
      "customer_context_ref": null,
      "business_context_ref": null
    }
  },
  "normalization_flags": [
    {
      "flag_code": "normalized_service_mode",
      "field": "service_context.service_mode",
      "from": "voyage repair",
      "to": "voyage_repair",
      "reason": "统一服务模式枚举"
    }
  ],
  "missing_fields": [
    {
      "field": "header_context.vessel_type",
      "required_for": ["pricing", "quote_document"],
      "severity": "medium",
      "reason": "船型缺失，可能影响历史参考和表头完整性",
      "suggested_source": "assessment_report"
    },
    {
      "field": "header_context.service_date",
      "required_for": ["pricing", "quote_document"],
      "severity": "medium",
      "reason": "服务日期缺失，影响部分场景费用和表头补齐",
      "suggested_source": "customer_context"
    }
  ]
}
```

---

## 15. MVP 开发建议

第一版建议先做以下能力：

1. 接收三类输入对象
2. 抽取基础表头事实
3. 归一服务模式、服务类别、地点类型
4. 生成 `candidate_items`
5. 输出结构化 `missing_fields`
6. 输出结构化 `normalization_flags`

第一版可以暂不做：

- 复杂冲突消解
- 深层语义合并
- 高级同义词扩展
- 跨来源置信度评分

---

## 16. 运行依赖与环境要求

## 16.1 当前实现所需依赖

第一个 Skill 当前分为两类依赖：

1. 核心运行依赖：仅 Python 标准库
2. 正式 Schema 校验依赖：`jsonschema`

也就是说：

- 当前 `skill.py` 和 `run.py` 在不安装第三方库的情况下即可运行
- 如果要对 `schemas/input.schema.json` 和 `schemas/output.schema.json` 做正式 JSON Schema 校验，需要额外安装 `jsonschema`

## 16.2 建议安装项

建议安装：

```bash
pip install jsonschema
```

若使用虚拟环境中的 Python，可执行：

```powershell
& ".opencode/.venv/Scripts/python.exe" -m pip install jsonschema
```

## 16.3 安装目的

安装 `jsonschema` 的目的不是运行第一个 Skill 本身，而是用于：

- 校验 Skill 输入是否符合 `input.schema.json`
- 校验 Skill 输出是否符合 `output.schema.json`
- 在联调阶段更早暴露结构偏差
- 为后续多个 Skill 复用统一契约校验能力

## 16.4 当前仓库状态说明

由于当前仓库还没有统一的 `requirements.txt`、`pyproject.toml` 或其他已验证的依赖管理配置，因此本阶段先在详细设计中显式记录该依赖，后续如确定统一依赖管理方式，再补正式依赖清单。

---

## 17. 验收标准

当本 Skill 达到以下效果时，可视为设计目标基本满足：

1. 能稳定消费评估单及补充上下文
2. 能输出结构统一的 `quote_request`
3. 能显式标记标准化动作
4. 能显式输出缺失关键字段
5. 不越界做可报价判断或金额计算
6. 输出结果可直接供后续 Skill 消费

---

## 18. 后续开发注意事项

- 本 Skill 的输出字段一旦进入联调，应尽量保持稳定，避免下游频繁跟改
- 若后续新增字段，优先追加在 `quote_request` 的上下文对象中，不要破坏已有结构
- 若评估单格式未来出现多个版本，优先在本 Skill 内做兼容，保持下游输入稳定

---

## 19. 后续优化与增强建议

当前第一个 Skill 已完成首版实现，但仍有多项增强点建议在后续迭代中补齐。

## 19.1 输入兼容性增强

- 扩展更多评估单字段别名映射，减少对上游字段命名的依赖
- 支持多版本评估单输入格式兼容
- 增强嵌套结构提取能力，而不只处理扁平字段

## 19.2 标准化规则增强

- 扩充服务类别、服务模式、地点类型的枚举映射表
- 引入更细粒度的冲突消解策略，而不只使用固定优先级
- 为标准化动作增加置信度或证据来源记录

## 19.3 候选项建模增强

- 更精确地区分服务项、备件项和其他费用项
- 从评估单中抽取更细粒度的工作范围、工时、人力、数量线索
- 支持对复杂任务做更稳定的候选项拆分，而不是只做简单标题归并
- 识别多方案线索并输出更明确的 `option_hints`

## 19.4 风险与待确认建模增强

- 更准确地区分风险提示、待确认项、假设条件三类信息
- 为待确认项增加来源分类，例如客户确认、现场确认、采购确认、工程师确认
- 对高风险缺失项增加更明确的严重度分级规则

## 19.5 契约与校验增强

- 将当前宽进严出的 schema 策略进一步细化，逐步增强输入 schema 的约束能力
- 在 `run.py` 中输出更友好的 schema 校验错误上下文
- 增加针对更多样例的自动化契约验证

## 19.6 工程化增强

- 将标准化映射表从代码中抽离为独立配置文件，便于维护
- 为核心标准化函数补单元测试
- 增加面向真实评估单样例的回归测试样本集
- 在后续统一依赖管理方案确定后，补正式依赖清单与校验命令
