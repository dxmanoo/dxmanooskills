#!/usr/bin/env python3
"""
query_builder.py — Obsidian Tasks Skill Query 文件生成脚本

用法:
  python3 query_builder.py create <output_file> <template_name> [--title TITLE] [--query QUERY]

模板:
  daily       — 今日看板
  weekly      — 本周任务看板
  priority    — 高优先级
  by-folder   — 按文件夹分组
  by-tags     — 按标签分组
  waiting     — 暂停/等待中
  recurring   — 循环任务总览
  recent-done — 最近已完成
  global      — 全局未完成（含 Urgency）
  inbox       — Inbox 收件箱
  no-date     — 无日期任务
  by-month    — 按截止月分组
  custom      — 自定义（需 --query 参数）
"""

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config" / "defaults.yaml"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    import yaml
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_vault_path(cfg: dict) -> Path:
    vault = cfg.get("vault_path", "").strip()
    if not vault:
        raise ValueError("vault_path 未配置。请先运行 config_manager.py init。")
    p = Path(vault)
    if not p.exists():
        raise ValueError(f"Vault 路径不存在: {vault}")
    return p


TEMPLATES = {

    "daily": """# 📋 今日任务

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

## 📅 今日可开始
```tasks
not done
starts before today
no due date
sort by path
```

## ✅ 今日已完成
```tasks
done
done today
sort by done
limit 20
```
""",

    "weekly": """# 📅 本周任务

## 🔥 今天到期
```tasks
not done
due today
sort by priority
group by folder
```

## 📆 本周到期
```tasks
not done
(due after today) AND (due before in 7 days)
sort by due
group by folder
```

## 🚫 尚未开始
```tasks
not done
starts before in 7 days
no due date
sort by path
```

## ✅ 本周完成
```tasks
done
done after yesterday
sort by done
limit 30
```
""",

    "priority": """# ⭐ 高优先级任务

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

## 最高优先级今日到期
```tasks
not done
priority is highest
due today
```
""",

    "by-folder": """# 📁 按项目分类

```tasks
not done
sort by folder
group by folder
```

---

## 📌 根目录任务
```tasks
not done
root
sort by path
```
""",

    "by-tags": """# 🏷️ 按标签分类

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

## #someday
```tasks
not done
tags include #someday
sort by due
```

## 无标签
```tasks
not done
no tags
sort by path
```
""",

    "waiting": """# ⏸️ 暂停/等待中

```tasks
status is ON_HOLD
sort by due
```

## 进行中
```tasks
status is IN_PROGRESS
sort by due
```
""",

    "recurring": """# 🔁 循环任务总览

## 未完成的循环任务
```tasks
not done
is recurring
sort by due
group by folder
```

## 今日到期的循环任务
```tasks
not done
is recurring
due today
```
""",

    "recent-done": """# ✅ 最近已完成

```tasks
done
done after yesterday
sort by done reverse
limit 50
```

## 本月完成
```tasks
done
done this month
sort by done reverse
limit 100
```
""",

    "global": """# 📊 全局未完成任务

> 按紧急度（Urgency）排序

```tasks
not done
sort by urgency reverse
group by folder
```

## 🔥 已过期
```tasks
not done
due before today
sort by urgency reverse
```

## ⏰ 今日到期
```tasks
not done
due today
sort by urgency reverse
```
""",

    "inbox": """# 📥 Inbox 收件箱

## 所有 Inbox 任务
```tasks
not done
folder includes Inbox
sort by created reverse
```

## 待分类（无标签）
```tasks
not done
folder includes Inbox
no tags
sort by path
```
""",

    "no-date": """# 📌 无日期任务

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
""",

    "by-month": """# 📆 按截止月分组

```tasks
not done
has due date
sort by due
group by due month
```
""",

    "review-daily": """# 📝 每日回顾

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

## 📋 明日预览
```tasks
not done
due tomorrow
sort by priority
```
""",
}


def create_query_file(vault: Path, output_path: str,
                      template_name: str, title: str = "",
                      custom_query: str = None) -> Path:
    target_dir = vault / os.path.dirname(output_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = vault / output_path

    if custom_query:
        lines = [f"# {title}\n```tasks\n{custom_query.strip()}\n```"]
        content = "\n".join(lines)
    elif template_name in TEMPLATES:
        content = TEMPLATES[template_name]
        if title:
            # 模板本身已有标题行 (# ...)，替换而不是追加
            lines = content.splitlines()
            if lines and lines[0].startswith("# "):
                lines[0] = f"# {title}"
            else:
                lines.insert(0, f"# {title}")
            content = "\n".join(lines)
    else:
        raise ValueError(
            f"未知模板: {template_name}\n"
            f"可用: {', '.join(TEMPLATES.keys())}"
        )

    target_file.write_text(content, encoding="utf-8")
    print(f"✅ Query 文件已创建: {target_file}")
    return target_file


def cli():
    if len(sys.argv) < 4:
        print(__doc__)
        print("\n可用模板:", ", ".join(TEMPLATES.keys()))
        sys.exit(1)

    cfg = load_config()
    vault = get_vault_path(cfg)

    output_file = sys.argv[2]
    template_name = sys.argv[3]
    title, custom_query = "", None
    args = sys.argv[4:]

    i = 0
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]; i += 2
        elif args[i] == "--query" and i + 1 < len(args):
            custom_query = args[i + 1]; i += 2
        else:
            i += 1

    if template_name == "custom" and not custom_query:
        print("⚠️  custom 模板需要 --query 参数")
        sys.exit(1)

    result = create_query_file(vault, output_file, template_name, title, custom_query)
    print(f"\n📄 完整路径: {result}")


if __name__ == "__main__":
    cli()
