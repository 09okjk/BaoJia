最佳实践
遵循这些指南来创建 Agent 可以有效使用的 skills。

编写清晰的描述
描述是 Agent 找到你的 skill 的方式。让它有价值。

具体明确
```
# 差 - 太模糊
description: 帮助处理文档

# 好 - 具体且可操作
description: 将 Word 文档（.docx）转换为 PDF 格式，保留格式和嵌入图像。当用户需要将文档导出或共享为 PDF 时使用。
```
包含触发关键词
考虑用户可能会说什么：

```
description: 分析 CSV 数据文件以生成汇总统计、图表和洞察。当用户提到数据分析、CSV 文件、统计或想要可视化数据时使用。
```
组织指令
使用清晰的标题
```
## 何时使用此 skill
## 前提条件
## 分步指令
## 示例
## 常见问题
```
明确步骤
```
## 指令

1. 首先，检查输入文件是否存在
2. 使用以下命令读取文件内容：`cat {filename}`
3. 运行以下命令处理内容：`python scripts/process.py {filename}`
4. 将输出返回给用户
```
包含确切命令
```
# 差
在文件上运行处理脚本。

# 好
运行：`python scripts/process.py --input data.csv --output results.json`

```
管理上下文大小
保持 SKILL.md 专注
指南	建议
主 SKILL.md	500 行以下
总 token 数	5000 个 token 以下
Reference 文件	按需加载
拆分大型 skills
如果你的 skill 变得太长：
```
# 不要一个大 skill：
mega-processor/
└── SKILL.md (1000+ 行)

# 创建专注的 skills：
text-processor/
└── SKILL.md (200 行)

image-processor/
└── SKILL.md (200 行)

data-processor/
└── SKILL.md (200 行)
```
使用 references 存放细节
```
## 快速开始

[基本指令 - 约 100 行]

## 高级用法

高级功能请参阅 [references/ADVANCED.md](references/ADVANCED.md)。

## API 参考

完整的 API 文档：[references/API.md](references/API.md)。

```
错误处理
预见失败
```
## 错误处理

### 找不到文件
如果输入文件不存在，通知用户并询问正确的路径。

### 无效格式
如果不支持文件格式，列出支持的格式并要求用户转换。

### 权限被拒绝
如果访问被拒绝，建议检查文件权限或以适当的访问权限运行。

```
提供恢复步骤
```
## 故障排除

### "找不到模块"错误
安装所需的依赖项：

pip install -r requirements.txt

### "连接被拒绝"错误
确保服务正在运行：

./scripts/start-service.sh
```
示例和边缘情况
显示输入/输出对
```
## 示例

### 基本用法

**输入：** "将 report.docx 转换为 PDF"

**操作：**

python scripts/convert.py report.docx --output report.pdf

**输出：** "成功创建 report.pdf"
```
覆盖边缘情况
```
## 边缘情况

### 空输入
如果用户提供空文件，返回警告而不是处理。

### 非常大的文件
对于超过 100MB 的文件，分块处理以避免内存问题：

python scripts/convert.py large-file.docx --chunked


### 文件名中的特殊字符
始终引用文件名以处理空格和特殊字符：

python scripts/convert.py "my file (copy).docx"
```
