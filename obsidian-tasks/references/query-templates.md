# Obsidian Tasks — Query Templates Library

> 以下为 `query_builder.py` 生成 `.md` 文件时可参考的模板库。
> 每个模板可直接嵌入 markdown 文件的 ` ```tasks ` 代码块中。
> 可根据用户需求组合、裁剪、嵌套使用。

---

## 模板 1：今日看板（Daily Dashboard）

```markdown
# 📋 今日任务

## 🔥 今日到期
```tasks
not done
due today
sort by priority
```

## ⏰ 已过期
```tasks
not done
due before today
sort by due
```

## 📅 今日开始可做
```tasks
not done
starts before today
no due date
sort by path
```
```

---

## 模板 2：本周任务看板（Weekly Dashboard）

```markdown
# 📅 本周任务

## 今天到期
```tasks
not done
due today
sort by priority
group by folder
```

## 本周到期
```tasks
not done
(due after today) AND (due before in 7 days)
sort by due
group by folder
```

## 本周可开始
```tasks
not done
starts before in 7 days
no due date
sort by path
```
```

---

## 模板 3：高优先级任务

```markdown
# ⭐ 高优先级

## 最高 + 高优先级
```tasks
not done
priority is above medium
sort by due
group by folder
```

## 无优先级但有截止日期
```tasks
not done
priority is none
has due date
sort by due
```
```

---

## 模板 4：按项目/标签分组看板

```markdown
# 🏷️ 按标签分类

## #work
```tasks
not done
tags include #work
sort by due
```

## #personal
```tasks
not done
tags include #personal
sort by due
```

## #someday（将来可能做）
```tasks
not done
tags include #someday
sort by due
```
```

---

## 模板 5：按文件夹分组

```markdown
# 📁 按项目分类

```tasks
not done
sort by folder
group by folder
```
```

---

## 模板 6：待开始（未来才生效的任务）

```markdown
# 🚫 尚未开始

## 今天之后才可开始
```tasks
not done
starts after today
sort by start
```

## 今天开始可做（含无开始日期）
```tasks
not done
starts before tomorrow
sort by start
```
```

---

## 模板 7：等待中 / 暂停

```markdown
# ⏸️ 暂停的任务

```tasks
status is ON_HOLD
sort by due
```
```

---

## 模板 8：循环任务总览

```markdown
# 🔁 循环任务

```tasks
not done
is recurring
sort by due
group by folder
```
```

---

## 模板 9：最近已完成

```markdown
# ✅ 最近完成

```tasks
done
done after yesterday
sort by done
limit 20
```
```

---

## 模板 10：全局未完成总览（带 Urgency 排序）

```markdown
# 📊 全局未完成任务

> 按紧急度排序，可快速判断处理优先级

```tasks
not done
sort by urgency reverse
group by folder
```
```

---

## 模板 11：无截止日期的任务

```markdown
# 📌 无日期任务

## 无截止日期
```tasks
not done
no due date
sort by path
group by folder
```

## 无计划日期但有截止日期
```tasks
not done
no scheduled date
has due date
sort by due
```
```

---

## 模板 12：按截止月分组

```markdown
# 📆 按月分组

```tasks
not done
has due date
sort by due
group by due month
```
```

---

## 模板 13：搜索特定路径

```markdown
# 🔍 项目A 任务

```tasks
not done
path includes ProjectA
sort by due
group by heading
```
```

---

## 模板 14：组合条件演示

```markdown
# 💼 工作 + 高优先级 + 本周到

```tasks
not done
tags include #work
priority is above medium
(due after yesterday) AND (due before in 7 days)
sort by due
group by folder
```
```

---

## 模板 15：Inbox 收件箱

```markdown
# 📥 Inbox

## 所有未归档任务
```tasks
not done
folder includes Inbox
sort by created reverse
```

## 无标签的 Inbox 任务（待分类）
```tasks
not done
folder includes Inbox
no tags
sort by path
```
```

---

## 模板 16：On Completion（循环任务专属视图）

```markdown
# 🆕 下一个循环实例

```tasks
not done
is recurring
filter by function task.recurrence?.isOnCompletion === true
sort by due
```
```

---

## 模板 17：自定义分组示例（JS）

```markdown
# 🎯 自定义分组

## 按"是否本周到期"分组
```tasks
not done
has due date
group by function task.due && task.due.isToday ? "今天" : (task.due.isWithinDays(7) ? "本周" : "更晚")
sort by due
```
```

---

## 模板 18：包含说明的查询（带 explain）

```markdown
# 📋 今日任务（含说明）

```tasks
not done
due today
explain
sort by priority
```
```

---

## 模板 19：空状态友好提示

```markdown
# 🎉 本周没有到期任务

```tasks
not done
(due after today) AND (due before in 7 days)
```

> 若上方显示为空，说明本周没有待办任务，好好休息！
```

---

## 模板 20：每日回顾模板

```markdown
# 📝 每日回顾 — {{DATE}}

## ✅ 今日完成
```tasks
done
done today
sort by done
```

## 🔥 今日到期但未完成
```tasks
not done
due today
sort by priority
```

## 📋 明日待办（预览）
```tasks
not done
due tomorrow
sort by priority
```
```

---

## 模板组合建议

| 用户需求 | 推荐模板 |
|---------|---------|
| 每日开机必看 | 模板1（今日看板）+ 模板9（昨日完成） |
| 项目管理 | 模板5（按文件夹）+ 模板6（待开始） |
| 高效优先级 | 模板3（高优先级）+ 模板10（全局Urgency） |
| Inbox 零库存 | 模板15（Inbox）+ 模板11（无日期） |
| 每周规划 | 模板2（本周）+ 模板8（循环） |
| 循环任务追踪 | 模板8（循环）+ 模板16（On Completion） |
