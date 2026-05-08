#!/usr/bin/env python3
"""
task_write.py — Obsidian Tasks Skill 任务写入脚本

用法:
  python3 task_write.py add <file> "<description>" [--priority PRIO] [--due DATE]
                                                    [--start DATE] [--scheduled DATE]
                                                    [--tags TAGS] [--recurrence RULE]
  python3 task_write.py done <file> <task_line>
  python3 task_write.py cancel <file> <task_line>
  python3 task_write.py modify <file> <old_line> <new_line>
  python3 task_write.py delete <file> <task_line>
"""

import sys
import re
import os
import subprocess
from pathlib import Path
from datetime import datetime, date

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config" / "defaults.yaml"


def load_config() -> dict:
    """加载配置"""
    if not CONFIG_FILE.exists():
        return {}
    import yaml
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_vault_path(cfg: dict) -> Path:
    """获取 vault 路径"""
    vault = cfg.get("vault_path", "").strip()
    if not vault:
        raise ValueError("vault_path 未配置。请先运行 config_manager.py init 或在对话中告知 AI 你的 vault 路径。")
    p = Path(vault)
    if not p.exists():
        raise ValueError(f"Vault 路径不存在: {vault}")
    return p


def resolve_file(cfg: dict, filename: str) -> Path:
    """解析文件路径（相对 vault 或绝对路径）"""
    vault = get_vault_path(cfg)
    if Path(filename).is_absolute():
        return Path(filename)
    return vault / filename


def today_str() -> str:
    return date.today().isoformat()


def format_date(d: str) -> str:
    """确保日期格式为 YYYY-MM-DD"""
    if not d:
        return ""
    d = d.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        return d
    try:
        result = subprocess.run(
            ["date", "-j", "-f", "%Y-%m-%d", d, "+%Y-%m-%d"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return d


def build_task_line(cfg: dict, description: str,
                    priority: str = "", due: str = "", start: str = "",
                    scheduled: str = "", tags: str = "", recurrence: str = "",
                    auto_created: bool = True) -> str:
    """
    构建一条完整的任务行（Emoji 格式）。
    """
    priority_map = {
        "highest": "🔺", "high": "⏫", "medium": "🔼",
        "low": "🔽", "lowest": "⏬", "none": ""
    }

    parts = [f"- [ ] {description}"]

    if priority:
        prio_emoji = priority_map.get(priority.lower(), "")
        if prio_emoji:
            parts.append(prio_emoji)

    if recurrence:
        parts.append(f"🔁 {recurrence}")

    if start:
        parts.append(f"🛫 {format_date(start)}")

    if scheduled:
        parts.append(f"⏳ {format_date(scheduled)}")

    if due:
        parts.append(f"📅 {format_date(due)}")

    if auto_created and cfg.get("auto_add_created_date", True):
        parts.append(f"➕ {today_str()}")

    if tags:
        tag_list = " ".join(f"#{t.strip().lstrip('#')}" for t in tags.split(","))
        parts.append(tag_list)

    return " ".join(parts)


def append_task_to_file(filepath: Path, task_line: str) -> None:
    """在文件末尾追加一行任务。"""
    if not filepath.exists():
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(f"{task_line}\n", encoding="utf-8")
        print(f"📄 新建文件并添加任务: {filepath}")
        return

    content = filepath.read_text(encoding="utf-8")
    if content and not content.endswith("\n"):
        content += "\n"
    content += f"{task_line}\n"
    filepath.write_text(content, encoding="utf-8")
    print(f"✅ 任务已添加至: {filepath}")


def mark_task_done(filepath: Path, task_line: str) -> None:
    """将任务标记为完成（加 ✅ 日期）。"""
    content = filepath.read_text(encoding="utf-8")
    if task_line not in content:
        raise ValueError(f"未在文件中找到该任务行: {task_line}")

    new_line = re.sub(r"\[ \]", "[x]", task_line)
    if "✅" not in new_line:
        new_line += f" ✅ {today_str()}"
    else:
        new_line = re.sub(r"✅ \d{4}-\d{2}-\d{2}", f"✅ {today_str()}", new_line)

    content = content.replace(task_line, new_line)
    filepath.write_text(content, encoding="utf-8")
    print(f"✅ 任务已标记完成: {new_line}")


def mark_task_cancelled(filepath: Path, task_line: str) -> None:
    """将任务标记为取消。"""
    content = filepath.read_text(encoding="utf-8")
    new_line = re.sub(r"\[ \]", "[-]", task_line)
    if "❌" not in new_line:
        new_line += f" ❌ {today_str()}"
    content = content.replace(task_line, new_line)
    filepath.write_text(content, encoding="utf-8")
    print(f"🚫 任务已取消: {new_line}")


def modify_task(filepath: Path, old_line: str, new_line: str) -> None:
    """修改任务行（精确替换）。"""
    content = filepath.read_text(encoding="utf-8")
    if old_line not in content:
        raise ValueError(f"未在文件中找到该任务行:\n{old_line}")
    content = content.replace(old_line, new_line, 1)
    filepath.write_text(content, encoding="utf-8")
    print(f"✏️  任务已修改")


def delete_task(filepath: Path, task_line: str) -> None:
    """删除任务行。"""
    content = filepath.read_text(encoding="utf-8")
    if task_line not in content:
        raise ValueError(f"未在文件中找到该任务行:\n{task_line}")
    content = content.replace(task_line + "\n", "")
    content = content.replace(task_line, "")
    filepath.write_text(content, encoding="utf-8")
    print(f"🗑️  任务已删除")


def cli():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cfg = load_config()
    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 4:
            print("用法: task_write.py add <file> <description> [options]")
            sys.exit(1)
        filename = sys.argv[2]
        description = sys.argv[3]

        priority, due, start, scheduled, tags, recurrence = "", "", "", "", "", ""
        for arg in sys.argv[4:]:
            if arg.startswith("--priority="):
                priority = arg.split("=", 1)[1]
            elif arg.startswith("--due="):
                due = arg.split("=", 1)[1]
            elif arg.startswith("--start="):
                start = arg.split("=", 1)[1]
            elif arg.startswith("--scheduled="):
                scheduled = arg.split("=", 1)[1]
            elif arg.startswith("--tags="):
                tags = arg.split("=", 1)[1]
            elif arg.startswith("--recurrence="):
                recurrence = arg.split("=", 1)[1]

        filepath = resolve_file(cfg, filename)
        line = build_task_line(cfg, description, priority, due, start, scheduled, tags, recurrence)
        append_task_to_file(filepath, line)

    elif cmd == "done":
        filename = sys.argv[2]
        task_line = sys.argv[3]
        filepath = resolve_file(cfg, filename)
        mark_task_done(filepath, task_line)

    elif cmd == "cancel":
        filename = sys.argv[2]
        task_line = sys.argv[3]
        filepath = resolve_file(cfg, filename)
        mark_task_cancelled(filepath, task_line)

    elif cmd == "modify":
        filename = sys.argv[2]
        old_line = sys.argv[3]
        new_line = sys.argv[4]
        filepath = resolve_file(cfg, filename)
        modify_task(filepath, old_line, new_line)

    elif cmd == "delete":
        filename = sys.argv[2]
        task_line = sys.argv[3]
        filepath = resolve_file(cfg, filename)
        delete_task(filepath, task_line)

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    cli()
