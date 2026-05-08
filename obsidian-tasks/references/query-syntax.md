# Obsidian Tasks — Query Syntax Reference

## 基础查询块

```markdown
```tasks
not done
due today
sort by priority
group by due
```
```

---

## 一、过滤器（Filters）

### 1. 状态过滤

| 指令 | 说明 |
|------|------|
| `not done` | 未完成（默认推荐） |
| `done` | 已完成 |
| `done today` | 今天完成 |
| `done this week` | 本周完成 |
| `done before YYYY-MM-DD` | 指定日期前完成 |
| `cancelled` | 已取消 |
| `not cancelled` | 未取消 |

### 2. 日期过滤

**单日过滤：**
| 指令 | 说明 |
|------|------|
| `due today` | 今天到期 |
| `due tomorrow` | 明天到期 |
| `due yesterday` | 昨天到期 |
| `due next Monday` | 下周一到期 |
| `due on 2026-05-10` | 指定日期到期 |
| `due before tomorrow` | 明天之前到期（含明天） |
| `due after yesterday` | 昨天之后到期（含昨天） |
| `due before 2026-05-10` | 指定日期之前 |
| `due after 2026-05-10` | 指定日期之后 |

**日期范围过滤：**
| 指令 | 说明 |
|------|------|
| `due 2026-05-01 2026-05-07` | 指定区间内到期 |
| `due in 7 days` | 7天内到期 |
| `due before in 7 days` | 7天内及之前到期 |
| `due after in 7 days` | 7天后到期 |

**相对日期：**
| 指令 | 说明 |
|------|------|
| `yesterday` / `today` / `tomorrow` | 相对今天 |
| `this week` / `this month` / `this quarter` / `this year` | 本周期 |
| `next week` / `next month` | 下周期 |
| `last week` / `last month` | 上周期 |
| `2 weeks ago` / `in 3 months` | 相对偏移 |
| `14th May` / `May` | 指定月日（今年） |

**日期空值过滤：**
| 指令 | 说明 |
|------|------|
| `no due date` | 无截止日期 |
| `has due date` | 有截止日期 |
| `no scheduled date` | 无计划日期 |
| `has scheduled date` | 有计划日期 |

### 3. 优先级过滤

| 指令 | 说明 |
|------|------|
| `priority is highest` | 最高优先级 |
| `priority is high` | 高优先级 |
| `priority is medium` | 中优先级 |
| `priority is low` | 低优先级 |
| `priority is lowest` | 最低优先级 |
| `priority is none` | 无优先级 |
| `priority is (above low)` | low 以上全部 |
| `priority is (below high)` | high 以下全部 |

### 4. 标签过滤

| 指令 | 说明 |
|------|------|
| `tags include #work` | 包含指定标签 |
| `tags do not include #work` | 不包含指定标签 |
| `has tags` | 有任意标签 |
| `no tags` | 无标签 |

### 5. 文本搜索

| 指令 | 说明 |
|------|------|
| `description includes buy` | 描述包含关键词 |
| `description does not include xxx` | 描述不包含 |
| `path includes Inbox` | 文件路径包含 |
| `folder includes Projects` | 文件夹名称包含 |
| `heading includes Tasks` | 标题包含 |
| `tag includes #work` | 标签包含 |

### 6. 递归任务过滤

| 指令 | 说明 |
|------|------|
| `is recurring` | 是循环任务 |
| `is not recurring` | 非循环任务 |

---

## 二、布尔组合

```text
(due before tomorrow) AND (is recurring)
(tags include #work) OR (tags include #personal)
NOT (tags include #someday)
```

**优先级**：`NOT` > `XOR` > `AND` > `OR`

**定界符**：`()` `[]` `{}` `""` 均可，需匹配使用。

---

## 三、排序（Sorting）

| 指令 | 说明 |
|------|------|
| `sort by due` | 按截止日期 |
| `sort by created` | 按创建日期 |
| `sort by done` | 按完成日期 |
| `sort by start` | 按开始日期 |
| `sort by scheduled` | 按计划日期 |
| `sort by priority` | 按优先级 |
| `sort by status` | 按状态 |
| `sort by status.type` | 按状态类型 |
| `sort by path` | 按文件路径 |
| `sort by folder` | 按文件夹 |
| `sort by heading` | 按标题 |
| `sort by relevance` | 按相关性 |
| `sort by urgency` | 按紧急度 |
| `sort by lineNumber` | 按原始行号 |
| `sort by ... reverse` | 反向排序（如 `sort by urgency reverse`） |

自定义排序（JavaScript）：
```text
sort by function !task.isDone
```

---

## 四、分组（Grouping）

| 指令 | 说明 |
|------|------|
| `group by due` | 按截止日期分组 |
| `group by due month` | 按截止月份分组 |
| `group by due week` | 按截止周分组 |
| `group by status` | 按状态分组 |
| `group by status.type` | 按状态类型 |
| `group by priority` | 按优先级 |
| `group by folder` | 按文件夹 |
| `group by path` | 按文件路径 |
| `group by heading` | 按标题 |
| `group by tags` | 按标签 |
| `group by filename` | 按文件名 |
| `group by regex matches /pattern/` | 按正则分组 |

自定义分组（JavaScript）：
```text
group by function task.isDone ? "已完成" : "未完成"
```

---

## 五、显示控制（Layout）

### 隐藏/显示任务元素
| 指令 | 说明 |
|------|------|
| `hide priority` | 隐藏优先级 |
| `hide due date` | 隐藏截止日期 |
| `hide start date` | 隐藏开始日期 |
| `hide scheduled date` | 隐藏计划日期 |
| `hide created date` | 隐藏创建日期 |
| `hide done date` | 隐藏完成日期 |
| `hide recurrence rule` | 隐藏重复规则 |
| `hide tags` | 隐藏标签 |
| `hide backlink` | 隐藏反向链接 |
| `hide task count` | 隐藏任务计数 |

### 显示可选元素
| 指令 | 说明 |
|------|------|
| `show urgency` | 显示紧急度分数 |
| `show toolbar` | 显示工具栏 |

### 限制结果
| 指令 | 说明 |
|------|------|
| `limit 10 tasks` | 只显示前10条 |
| `limit 1 tasks` | 只显示1条 |

---

## 六、调试

| 指令 | 说明 |
|------|------|
| `explain` | 展开日期、显示布尔逻辑 |
| `explain this` | 同上（等效） |

---

## 七、路径/文件过滤

| 指令 | 说明 |
|------|------|
| `root` | 只搜索根目录文件 |
| `folder includes Projects` | 文件夹名包含 |
| `path includes Inbox` | 路径包含 |
| `path regex matches /pattern/` | 正则匹配路径 |
| `file includes filename` | 文件名包含 |
| `heading includes Tasks` | 标题包含 |

---

## 八、注释

```text
# 今天要做的事
not done
due today

# 将来要做的事
not done
due after tomorrow
```
