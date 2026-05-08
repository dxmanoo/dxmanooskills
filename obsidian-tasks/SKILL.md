---
name: obsidian-tasks
description: |
  Obsidian Tasks 插件操作技能。当用户提到以下场景时使用：
  - 管理 Obsidian 任务（新建、完成、修改、删除）
  - 在 Obsidian 里添加待办事项
  - 查找/搜索 Obsidian 中的任务
  - 生成 Obsidian Tasks query 看板/Dashboard 文件
  - 创建每日任务视图、本周任务看板
  - 查询今日到期、本周到期、高优先级的任务
  - 管理 Obsidian Tasks 插件的配置
  - 查看/修改 vault 路径、任务格式等设置
  - 任何涉及 Obsidian 插件 Tasks 的操作

  触发词示例：
  "帮我加个任务"、"记一笔 todo"、"查一下今天到期的任务"、"生成一个 query 文件"、
  "创建每日看板"、"搜索未完成的任务"、"把配置改成 dataview 格式"
---

# Obsidian Tasks Skill

使用 Obsidian Tasks 插件管理 vault 中的任务。支持新建/修改/删除任务、搜索任务、生成 Query Dashboard 文件、配置管理。

## 核心文件

```
<skill-base-dir>/
├── config/defaults.yaml      ← 用户配置（首次由 AI 填写）
├── scripts/
│   ├── config_manager.py    ← 配置管理（查看/修改/重置）
│   ├── task_write.py        ← 任务写入（新建/完成/修改/删除）
│   ├── task_read.py         ← 任务读取（搜索/列表/统计）
│   └── query_builder.py     ← Query 文件生成（Dashboard 看板）
└── references/
    ├── task-format.md        ← Emoji 格式完整参考
    ├── query-syntax.md       ← Query 语法完整参考
    └── query-templates.md   ← 20个 Query 模板库
```

## 第一步：检查配置

每次操作前，先读取 `config/defaults.yaml`（相对于 skill 基础目录）。

如果 `first_run_done` 为 `false` 或 `vault_path` 为空，**必须先询问用户**以下 4 个问题，填写配置后再继续：

1. **vault 路径**：你的 Obsidian vault 根目录在哪？（绝对路径）
2. **任务格式**：用 Emoji 格式还是 Dataview 格式？
3. **默认 Inbox 文件**：新建任务默认写到哪个 `.md` 文件？
4. **Query 目录**：Query 看板文件生成到哪个目录？

询问时明确告诉用户：这是首次配置，回答后会保存，之后可以直接使用。

## 第二步：路由判断

根据用户意图选择正确的操作：

| 用户意图 | 脚本 | 关键参数 |
|---------|------|---------|
| 查看/修改配置 | `config_manager.py` | `show` / `set key value` / `reset` |
| 新建任务 | `task_write.py add` | `--file`, `--desc`, `--due`, `--priority`, `--tags` |
| 完成任务 | `task_write.py done` | 需提供完整任务行文本 |
| 修改任务 | `task_write.py modify` | 需提供原行和新行 |
| 删除任务 | `task_write.py delete` | 需提供完整任务行 |
| 搜索任务 | `task_read.py search` | `--status`, `--due`, `--priority`, `--tags`, `--text` |
| 列出文件内任务 | `task_read.py list` | 文件名 |
| 统计任务 | `task_read.py stats` | 无参数 |
| 生成 Query 文件 | `query_builder.py create` | 模板名 + `--title` |

## 第三步：执行并向用户报告

所有脚本执行后，**明确告知用户**：
- 操作结果（任务已添加/修改/删除）
- 涉及的文件路径
- 涉及的关键内容（如任务描述、日期等）

**如果脚本出错**，检查原因后给出清晰的修复建议。

## 配置管理（config_manager.py）

```bash
# 查看当前配置
python3 <skill-base-dir>/scripts/config_manager.py show

# 修改单个配置项
python3 <skill-base-dir>/scripts/config_manager.py set vault_path "/Users/xxx/Obsidian/Vault"

# 重置配置（重新初始化）
python3 <skill-base-dir>/scripts/config_manager.py reset
```

**配置更新后，AI 必须显式告诉用户**："已更新配置：`vault_path` = ..."

## 任务写入（task_write.py）

### 新建任务
```bash
python3 <skill-base-dir>/scripts/task_write.py add "<file>" "<description>" \
  [--priority=high] \
  [--due=YYYY-MM-DD] \
  [--start=YYYY-MM-DD] \
  [--scheduled=YYYY-MM-DD] \
  [--tags=work,project] \
  [--recurrence="every week"]
```

### 完成任务
```bash
python3 <skill-base-dir>/scripts/task_write.py done "<file>" "<task_line>"
```
> 提供的是任务行的**完整文本**（精确匹配，包括所有 emoji 和日期）。先用 `task_read.py search` 确认。

### 修改任务
```bash
python3 <skill-base-dir>/scripts/task_write.py modify "<file>" "<old_line>" "<new_line>"
```

### 删除任务
```bash
python3 <skill-base-dir>/scripts/task_write.py delete "<file>" "<task_line>"
```

## 任务读取（task_read.py）

### 搜索任务
```bash
# 今日到期的未完成任务
python3 <skill-base-dir>/scripts/task_read.py search --status=not_done --due=today

# 高优先级任务
python3 <skill-base-dir>/scripts/task_read.py search --status=not_done --priority=high

# 带特定标签的任务
python3 <skill-base-dir>/scripts/task_read.py search --tags=work

# 包含关键词的任务
python3 <skill-base-dir>/scripts/task_read.py search --text="报告"

# 指定路径搜索
python3 <skill-base-dir>/scripts/task_read.py search --path="/Users/xxx/Obsidian/Vault/Projects"

# 统计
python3 <skill-base-dir>/scripts/task_read.py stats
```

### 列出文件内任务
```bash
python3 <skill-base-dir>/scripts/task_read.py list "Inbox.md"
```

## Query 文件生成（query_builder.py）← 核心功能

生成 `.md` 文件，包含 Obsidian Tasks 插件的 query 代码块，生成后在 Obsidian 中打开即可查看。

### 内置模板

| 模板名 | 说明 |
|--------|------|
| `daily` | 今日看板（今日到期 + 已过期 + 今日可开始 + 今日完成） |
| `weekly` | 本周任务（今天到期 + 本周到期 + 尚未开始 + 本周完成） |
| `priority` | 高优先级（最高/高优先级 + 无优先级但有截止） |
| `by-folder` | 按文件夹分组 |
| `by-tags` | 按标签分组（#work, #personal, #someday, 无标签） |
| `waiting` | 暂停/进行中任务 |
| `recurring` | 循环任务总览 |
| `recent-done` | 最近已完成 |
| `global` | 全局未完成（按 Urgency 排序 + 已过期 + 今日到期） |
| `inbox` | Inbox 收件箱 |
| `no-date` | 无日期任务 |
| `by-month` | 按截止月分组 |
| `review-daily` | 每日回顾模板 |
| `custom` | 自定义（需配合 --query） |

### 用法

```bash
# 生成今日看板
python3 <skill-base-dir>/scripts/query_builder.py create "Dashboards/今日看板.md" daily \
  --title "📋 今日任务"

# 生成自定义 query
python3 <skill-base-dir>/scripts/query_builder.py create "Dashboards/我的看板.md" custom \
  --title "🎯 我的任务" \
  --query "not done\ndue before in 7 days\nsort by priority\ngroup by folder"
```

> `query-templates.md`（references/ 目录下）有 20 个完整模板文件内容供参考。

## 任务格式速查（Emoji 格式）

```
- [ ] 任务描述 🔼 📅 2026-05-10 ➕ 2026-05-07 #tag
```

| 符号 | 含义 |
|------|------|
| `[ ]` | 待办 `[x]` 已完成 `[/]` 进行中 `[-]` 取消 |
| `🔺` `⏫` `🔼` `🔽` `⏬` | 优先级：最高/高/中/低/最低 |
| `🛫` | 开始日期 `⏳` 计划日期 `📅` 截止日期 |
| `➕` | 创建日期 `✅` 完成日期 |
| `🔁 every week` | 重复 |

详细格式规范见 `references/task-format.md`。

## Query 语法速查

```
# 过滤
not done
due today
due before in 7 days
priority is high
tags include #work
path includes ProjectA

# 排序
sort by due
sort by priority
sort by urgency
sort by due reverse

# 分组
group by due
group by folder
group by tags

# 显示控制
hide due date
show urgency
limit 10 tasks
explain

# 布尔组合
(due before tomorrow) AND (is recurring)
(tags include #work) OR (tags include #personal)
NOT (tags include #someday)
```

完整语法见 `references/query-syntax.md`。

## 注意事项

1. **修改文件时**：使用 `replace_in_file` 精确替换任务行，**不要**重写整个文件。
2. **vault 路径**：所有脚本通过 config 中的 `vault_path` 自动拼接，不写死。
3. **日期格式**：`YYYY-MM-DD`，脚本自动处理。
4. **任务行精确性**：完成/修改/删除需要提供任务的精确文本，先用 `task_read.py search` 确认。
5. **Query 文件**：生成后告诉用户文件路径，以及如何在 Obsidian 中查看。
6. **脚本工作目录**：执行脚本时建议 `cd` 到 vault 根目录，或使用绝对路径调用脚本。

## 错误处理

| 情况 | 处理 |
|------|------|
| `vault_path` 为空 | 先询问用户，填写配置 |
| `vault_path` 指向不存在的路径 | 告知用户路径无效，重新询问 |
| 找不到要修改的任务行 | 用 `task_read.py search` 重新搜索，确认任务文本 |
| 脚本执行失败 | 检查 Python 环境和参数，报告具体错误信息 |
| 用户要修改配置 | 用 `config_manager.py set` 修改，明确告诉用户改动内容 |
