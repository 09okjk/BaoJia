# OpenClaw Skill 创建规范 🛠️

## 📁 核心目录结构

```
my-skill/
├── SKILL.md              # 【必需】技能定义文件
├── _meta.json            # 【可选】元数据（版本、作者等）
├── .env.example          # 【可选】环境变量示例
├── .gitignore            # 【可选】Git 忽略规则
├── README.md             # 【可选】使用说明
├── scripts/              # 【可选】脚本目录
│   ├── main.py           # 主脚本（Python）
│   ├── main.mjs          # 主脚本（Node.js ESM）
│   └── helper.py         # 辅助脚本
├── references/           # 【可选】参考资料目录
│   ├── config.md         # 配置说明
│   └── *.schema.json     # JSON Schema 定义
└── samples/              # 【可选】测试样本目录
    └── *.json            # 测试输入/输出样本
```

### 目录说明

| 目录/文件 | 用途 | 必需 |
|-----------|------|------|
| `SKILL.md` | 技能定义 + 使用文档 | ✅ 必需 |
| `scripts/` | 可执行脚本 | ⚠️ 功能性技能需要 |
| `references/` | 参考资料、配置模板、Schema | ❌ 可选 |
| `samples/` | 测试样本、示例输入输出 | ❌ 可选 |
| `.env.example` | 环境变量模板 | ⚠️ 需要配置时推荐 |
| `_meta.json` | ClawHub 元数据 | ❌ 可选 |

---

## 📄 SKILL.md 格式（核心文件）

### 1. Front Matter（YAML 头部）

```yaml
---
name: parse-requirement-skill          # 【必需】与 slug 一致，小写连字符
slug: parse-requirement-skill          # 【必需】小写连字符，用于 URL/标识
version: 2.0.0                         # 【必需】语义化版本 (MAJOR.MINOR.PATCH)
author: "09okjk"                       # 【可选】作者/团队名称
homepage: https://...                  # 【可选】项目主页
description: 一句话描述技能的用途     # 【必需】简洁描述
changelog: |                           # 【可选】版本升级时必需
  ## [2.0.0] - 交互闭环版
  - 新增 parse / revise / confirm 三阶段支持
  - 新增 session_id 和 revision_history 支持
metadata:
  clawdbot:
    emoji: 🎯                          # 【可选】Emoji 标识
    requires:
      bins: ["python3", "node"]        # 【可选】需要的命令行工具
      env: ["API_KEY"]                 # 【可选】需要的环境变量
    os: ["linux", "darwin", "win32"]   # 【可选】支持的操作系统
---
```

### Front Matter 规范

| 字段 | 格式要求 | 说明 |
|------|----------|------|
| `name` | 小写连字符 | 必须与 `slug` 保持一致 |
| `slug` | 小写连字符 | 用于 URL、标识符，如 `parse-requirement-skill` |
| `version` | 语义化版本 | 遵循 SemVer 规范，`SKILL.md` 与 `_meta.json` 必须同步 |
| `author` | 字符串 | 推荐填写，便于归属 |
| `changelog` | Markdown | 版本升级时必需，记录变更内容 |

### 2. 正文内容（Markdown）

```markdown
# 技能名称

简短介绍。

## When to Use（何时使用）

✅ 使用场景列表
- 用户说 "xxx" 时
- 需要 xxx 功能时

## When NOT to Use（何时不用）

❌ 不适用场景
- xxx 情况请用其他方法

## Setup（安装配置）

分步骤说明安装、配置、初始化流程。

### Python 技能示例

```bash
# 1. 安装依赖（如有）
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 3. 运行测试
python3 {baseDir}/scripts/main.py --action parse --input "测试输入" --refs {baseDir}/references/config.json
```

### Node.js 技能示例

```bash
# 1. 安装依赖
cd {baseDir}
npm install

# 2. 配置环境变量
cp .env.example .env

# 3. 运行测试
node {baseDir}/scripts/main.mjs --input ./input.json
```

## Options（选项说明）

### 通用选项

| 选项 | 类型 | 说明 | 必需 |
|------|------|------|------|
| `--action` | `parse\|revise\|confirm` | 指定执行阶段 | ⚠️ 多阶段技能需要 |
| `--input` | `string` | 原始输入文本 | ❌ 与 `--json-input` 二选一 |
| `--json-input` | `json` | 直接传 JSON 输入 | ❌ 与 `--input` 二选一 |
| `--refs` | `path` | 参考文件路径 | ⚠️ 需要枚举映射时需要 |
| `--pretty` | `flag` | 格式化输出 JSON | ❌ 可选 |

### 各阶段参数说明

如技能支持多阶段（如 parse/revise/confirm），需明确各阶段可用参数。

## Core Rules（核心规则）

重要的技术细节、注意事项、常见陷阱。

## Security & Privacy（安全说明）

- 数据处理方式（本地/云端）
- 隐私保护措施
- 敏感信息处理建议
- 数据库/API 权限最小化原则

### 环境变量安全

```bash
# .env.example 模板
API_KEY=              # 敏感信息，切勿提交 .env 到版本控制
DB_HOST=localhost
DB_PORT=5432
LOG_LEVEL=INFO
```

## Related Skills（相关技能）

列出推荐配合使用的其他技能，形成工作流。

```markdown
- `search-history-cases-skill`: 历史案例检索
- `match-risks-skill`: 风险匹配
- `generate-report-skill`: 报告生成
```

## Feedback（反馈）

- 有用请 star
- 更新请 sync
- 问题请提 issue
```

---

## 🔑 关键规范

### 文件/目录规范

| 文件/目录 | 作用 | 必需 | 说明 |
|-----------|------|------|------|
| `SKILL.md` | 技能定义 + 使用文档 | ✅ 必需 | 包含 Front Matter 和正文 |
| `scripts/` | 可执行脚本 | ⚠️ 功能性技能需要 | 主脚本建议命名 `main.py` 或 `main.mjs` |
| `references/` | 参考资料、配置模板 | ❌ 可选 | 可包含 `config.md`、`.schema.json` 等 |
| `samples/` | 测试样本 | ❌ 可选 | 推荐存放测试输入输出 JSON |
| `.env.example` | 环境变量模板 | ⚠️ 需要配置时推荐 | 切勿提交 `.env` 到版本控制 |
| `_meta.json` | ClawHub 元数据 | ❌ 可选 | 与 `SKILL.md` Front Matter 保持同步 |
| `.gitignore` | Git 忽略规则 | ⚠️ 推荐 | 忽略 `.env`、`__pycache__/` 等 |

### 版本一致性

**重要**: `SKILL.md` 和 `_meta.json` 的 `version` 字段必须保持同步。

```yaml
# SKILL.md
version: 2.0.0
```

```json
// _meta.json
{
  "version": "2.0.0"
}
```

### 命名规范

| 项目 | 规范 | 示例 |
|------|------|------|
| `name` / `slug` | 小写连字符 | `parse-requirement-skill` |
| 脚本文件 | `snake_case` 或 `kebab-case` | `main.py`, `helper.py` |
| 配置文件 | `kebab-case` | `r2-sample-enums.json` |
| Schema 文件 | 描述性命名 | `requirement-input.schema.json` |

### .gitignore 推荐内容

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.venv/
venv/
.env

# Node.js
node_modules/
dist/

# 通用
.DS_Store
.idea/
.vscode/
*.log
```

---

## 📝 示例参考

### 简单技能（如 tavily-search）

```
tavily-search/
├── SKILL.md
├── _meta.json
└── scripts/
    ├── search.mjs
    └── extract.mjs
```

**特点**: 单一功能，无复杂配置，直接调用 API。

---

### 复杂技能（如 email-automation）

```
email-automation/
├── SKILL.md
├── README.md
├── .env.example
├── .gitignore
├── _meta.json
├── scripts/
│   ├── main.py
│   └── email_processor.py
├── references/
│   ├── config.md
│   └── email-template.schema.json
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

**特点**: 多模块协作，需要配置，有 Schema 验证和测试样本。

---

### 数据驱动技能（如 parse-requirement-skill）

```
parse-requirement-skill/
├── SKILL.md
├── README.md
├── _meta.json
├── .env.example
├── .gitignore
├── scripts/
│   └── main.py
├── references/
│   ├── config.md              # 配置说明
│   ├── r2-sample-enums.json   # 枚举映射
│   ├── aliases.json           # 别名词典
│   └── *.schema.json          # JSON Schema 定义
└── samples/
    ├── sample-input.json
    ├── sample-revise-input.json
    └── sample-confirm-input.json
```

**特点**: 依赖参考数据，支持多阶段交互，有完整测试样本。

---

## 🚀 快速开始

### 步骤 1: 创建目录

```bash
mkdir my-skill && cd my-skill
```

### 步骤 2: 写 SKILL.md

按 Front Matter + 正文格式填写，确保：
- `name` 与 `slug` 一致（小写连字符）
- `version` 为语义化版本
- 包含 When to Use / NOT to Use

### 步骤 3: 加脚本（如需要）

```bash
mkdir scripts
# 创建主脚本 main.py 或 main.mjs
```

### 步骤 4: 配置参考数据（如需要）

```bash
mkdir references
mkdir samples
# 添加枚举映射、Schema、测试样本
```

### 步骤 5: 测试

```bash
# Python 技能
python3 scripts/main.py --action parse --input "测试" --refs references/config.json --pretty

# Node.js 技能
node scripts/main.mjs --input ./input.json --pretty
```

### 步骤 6: 发布（可选）

```bash
# 发布到 ClawHub
clawhub publish
```

---

## 📚 附录：最佳实践

### 1. 版本管理

- 遵循 SemVer 规范
- 重大变更升级 MAJOR 版本
- 新功能升级 MINOR 版本
- 修复 bug 升级 PATCH 版本
- `SKILL.md` 和 `_meta.json` 版本号保持同步

### 2. 文档质量

- `description` 一句话讲清用途
- `When to Use` 明确适用场景
- `When NOT to Use` 避免误用
- 提供可运行的示例命令

### 3. 测试样本

- 在 `samples/` 中提供典型输入输出
- 覆盖正常场景和边界场景
- 便于回归测试和演示

### 4. 安全合规

- 不提交 `.env` 等敏感文件
- 数据库账号使用最小权限
- 日志中脱敏敏感信息

---

*最后更新：2026-03-23*