# Obsidian Tasks — Emoji Task Format Reference

## 标准任务行格式

```
- [ ] 任务描述 🔼 ⏫ 🔁 every week 🛫 2026-05-01 ⏳ 2026-05-07 📅 2026-05-10 ➕ 2026-05-07 ✅ 2026-05-10
```

各字段顺序任意，可混排。

---

## 状态（Status）

| 符号 | 名称 | 类型 | 说明 |
|------|------|------|------|
| `[ ]` | Todo | TODO | 未完成（默认） |
| `[x]` | Done | DONE | 已完成 |
| `[/]` | In Progress | IN_PROGRESS | 进行中 |
| `[-]` | Cancelled | CANCELLED | 已取消 |
| `[>]` | On Hold | ON_HOLD | 暂停 |
| `[?]` | Non Task | NON_TASK | 非任务 |

完成时自动添加 `✅ YYYY-MM-DD`。

---

## 优先级（Priority）

| 符号 | 名称 | Urgency 分值 |
|------|------|-------------|
| 🔺 | Highest | +6.0 |
| ⏫ | High | +5.0 |
| 🔼 | Medium | +3.0 |
| 无 | None | +1.5（默认） |
| 🔽 | Low | +0.5 |
| ⏬ | Lowest | +0.0 |

---

## 日期（Dates）

| 符号 | 名称 | 说明 |
|------|------|------|
| 🛫 | Start date | 可以开始日期（隐藏任务直到该日期） |
| ⏳ | Scheduled date | 计划工作日期 |
| 📅 | Due date | 截止日期 |
| ➕ | Created date | 创建日期 |
| ✅ | Done date | 完成日期 |
| ❌ | Cancelled date | 取消日期 |

日期格式：`YYYY-MM-DD`（或自由文本如 `next monday`）。

---

## 重复（Recurrence）

```
🔁 every day
🔁 every week
🔁 every month
🔁 every year
🔁 every Monday
🔁 every weekday
🔁 every week on Monday
🔁 every 2 weeks
🔁 every 3 months
```

重复基准：
- `when done` — 基于完成日期（默认）
- 无 — 基于原始日期

示例：
```
- [ ] 浇水 🔁 every 3 days
- [ ] 体检 🔁 every year on March 15
- [ ] 写周报 🔁 every week on Monday
```

---

## 标签（Tags）

标签可在任务行的任意位置，格式：`#tag-name`。

```
- [ ] 开会 #meetings #work
- [ ] 买书 #shopping 🛫 2026-06-01 📅 2026-06-07
```

---

## 依赖（Dependencies）

| 符号 | 字段 | 示例 |
|------|------|------|
| 无 | id | `id:: abc123` |
| 无 | depends on | `depends:: abc123` |

```
- [ ] 任务A id:: abc123
- [ ] 任务B depends:: abc123
```

---

## 完整示例

```
- [ ] 写项目报告 🔼 📅 2026-05-15 #project
- [x] 提交代码 ⏫ 📅 2026-05-10 ✅ 2026-05-10 #code
- [ ] 周会 🔁 every Monday 🛫 2026-05-11 ⏳ 2026-05-12 📅 2026-05-13 #meetings
- [/] 设计数据库 ⏫ 🛫 2026-05-01 #design
```

---

## 注意事项

1. **emoji 顺序无关** — Tasks 插件按语义识别，不按位置。
2. **空格** — emoji 和日期之间有空格：`📅 2026-05-10`。
3. **中文字符兼容** — 任务描述可用中文，emoji 和日期保持 ASCII。
4. **修改任务时** — 使用 replace_in_file 精确替换那一行，不要重写整个文件。
5. **新增任务** — 在目标文件末尾插入新行，以 `\n- [ ]` 开头。
