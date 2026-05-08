#!/usr/bin/env python3
"""
task_read.py — Obsidian Tasks Skill 任务读取/搜索脚本

用法:
  python3 task_read.py search [--path DIR] [--status STATUS] [--due DATE_EXPR]
                              [--priority PRIO] [--tags TAG] [--text TEXT]
                              [--limit N]
  python3 task_read.py list <file>
  python3 task_read.py stats [--path DIR]
"""

import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime, date, timedelta

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


def today() -> date:
    return date.today()


def parse_date_expr(expr: str) -> tuple:
    t = today()
    expr = expr.strip().lower()
    if expr in ("today",):
        return t, t
    elif expr == "tomorrow":
        return t + timedelta(days=1), t + timedelta(days=1)
    elif expr == "yesterday":
        return t - timedelta(days=1), t - timedelta(days=1)
    elif re.search(r"in\s+(\d+)\s+days?", expr):
        m = re.search(r"in\s+(\d+)\s+days?", expr)
        days = int(m.group(1))
        return t, t + timedelta(days=days)
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", expr):
        d = datetime.strptime(expr, "%Y-%m-%d").date()
        return d, d
    else:
        try:
            result = subprocess.run(
                ["date", "-j", "+%Y-%m-%d", expr],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                d = datetime.strptime(result.stdout.strip(), "%Y-%m-%d").date()
                return d, d
        except Exception:
            pass
        return t, t


TASK_PATTERN = re.compile(
    r'^(\s*)-\s*\[([ x\-/<>?])\]\s*(.*)',
    re.IGNORECASE
)


def parse_task_line(line: str) -> dict:
    m = TASK_PATTERN.match(line)
    if not m:
        return {}
    indent, status, rest = m.group(1), m.group(2), m.group(3)
    task = {
        "raw": line,
        "indent": indent,
        "status_char": status,
        "is_done": status.lower() == "x",
        "is_cancelled": status == "-",
        "is_in_progress": status == "/",
        "is_on_hold": status == ">",
        "description": rest,
    }
    # Priority
    if "🔺" in rest:
        task["priority"] = "highest"
    elif "⏫" in rest:
        task["priority"] = "high"
    elif "🔼" in rest:
        task["priority"] = "medium"
    elif "🔽" in rest:
        task["priority"] = "low"
    elif "⏬" in rest:
        task["priority"] = "lowest"
    else:
        task["priority"] = "none"
    # Dates
    def extract_date(emoji):
        m = re.search(rf"{re.escape(emoji)}\s*(\d{4}-\d{2}-\d{2})", rest)
        return m.group(1) if m else None
    task["start_date"] = extract_date("🛫")
    task["scheduled_date"] = extract_date("⏳")
    task["due_date"] = extract_date("📅")
    task["created_date"] = extract_date("➕")
    task["done_date"] = extract_date("✅")
    # Tags
    task["tags"] = re.findall(r"#[^\s#,]+", rest)
    # Recurring
    task["is_recurring"] = "🔁" in rest
    return task


def scan_vault(vault_root: Path) -> list:
    tasks = []
    for md_file in vault_root.rglob("*.md"):
        if not md_file.is_file():
            continue
        try:
            lines = md_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if TASK_PATTERN.match(line):
                t = parse_task_line(line)
                t["file"] = str(md_file.relative_to(vault_root))
                t["file_abs"] = str(md_file)
                t["line_num"] = i + 1
                tasks.append(t)
    return tasks


def filter_tasks(tasks: list, status=None,
                 due_from=None, due_to=None,
                 priority=None, tags=None, text=None) -> list:
    result = tasks
    if status == "done":
        result = [t for t in result if t.get("is_done")]
    elif status in ("not_done", "not done"):
        result = [t for t in result if not t.get("is_done") and not t.get("is_cancelled")]
    if due_from:
        result = [t for t in result if t.get("due_date") and
                  datetime.strptime(t["due_date"], "%Y-%m-%d").date() >= due_from]
    if due_to:
        result = [t for t in result if t.get("due_date") and
                  datetime.strptime(t["due_date"], "%Y-%m-%d").date() <= due_to]
    if priority:
        result = [t for t in result if t.get("priority") == priority.lower()]
    if tags:
        for tag in tags:
            result = [t for t in result if tag in t.get("tags", [])]
    if text:
        result = [t for t in result if text.lower() in t.get("description", "").lower()]
    return result


def format_task_line(t: dict) -> str:
    status_map = {"x": "✅", "-": "🚫", "/": "🏃", ">": "⏸️", " ": "  "}
    s = status_map.get(t.get("status_char", " "), "  ")
    desc = t.get("description", "")[:60]
    due = f" 📅{t['due_date']}" if t.get("due_date") else ""
    prio = f" {t.get('priority','')}" if t.get('priority') != 'none' else ""
    tags_str = " " + " ".join(t.get("tags", [])) if t.get("tags") else ""
    return f"[{t['file']}:{t['line_num']}] {s} {desc}{due}{prio}{tags_str}"


def cmd_search(cfg: dict, args: list) -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--due", default=None)
    parser.add_argument("--priority", default=None)
    parser.add_argument("--tags", default=None)
    parser.add_argument("--text", default=None)
    parser.add_argument("--limit", type=int, default=100)
    parsed, _ = parser.parse_known_args(args)

    vault = Path(parsed.path) if parsed.path else get_vault_path(cfg)
    due_from, due_to = None, None
    if parsed.due:
        due_from, due_to = parse_date_expr(parsed.due)
    tags = parsed.tags.split(",") if parsed.tags else None

    tasks = scan_vault(vault)
    tasks = filter_tasks(tasks, status=parsed.status,
                          due_from=due_from, due_to=due_to,
                          priority=parsed.priority,
                          tags=tags, text=parsed.text)

    print(f"🔍 找到 {len(tasks)} 个任务（最多显示 {parsed.limit} 条）：\n")
    for t in tasks[:parsed.limit]:
        print(format_task_line(t))
    if len(tasks) > parsed.limit:
        print(f"\n... 还有 {len(tasks) - parsed.limit} 条未显示")


def cmd_list(cfg: dict, filename: str) -> None:
    vault = get_vault_path(cfg)
    filepath = vault / filename if not Path(filename).is_absolute() else Path(filename)
    if not filepath.exists():
        print(f"⚠️  文件不存在: {filepath}")
        return
    lines = filepath.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if TASK_PATTERN.match(line):
            t = parse_task_line(line)
            t["file"] = str(filepath.relative_to(vault))
            t["line_num"] = i + 1
            print(format_task_line(t))


def cmd_stats(cfg: dict, path_arg: str = None) -> None:
    vault = Path(path_arg) if path_arg else get_vault_path(cfg)
    tasks = scan_vault(vault)
    total = len(tasks)
    done = len([t for t in tasks if t.get("is_done")])
    not_done = total - done
    t_today = today()
    overdue = [t for t in tasks if not t.get("is_done") and t.get("due_date") and
               datetime.strptime(t["due_date"], "%Y-%m-%d").date() < t_today]
    today_due = [t for t in tasks if not t.get("is_done") and t.get("due_date") and
                 datetime.strptime(t["due_date"], "%Y-%m-%d").date() == t_today]
    print(f"📊 Vault 统计 — {vault.name}")
    print(f"  总任务数: {total}")
    print(f"  已完成:   {done} ({100*done/total:.0f}%)" if total else "  已完成: 0")
    print(f"  未完成:   {not_done}")
    print(f"  今日到期: {len(today_due)}")
    print(f"  已过期:   {len(overdue)}")


def cli():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cfg = load_config()
    cmd = sys.argv[1]
    if cmd == "search":
        cmd_search(cfg, sys.argv[2:])
    elif cmd == "list":
        if len(sys.argv) < 3:
            print("用法: task_read.py list <file>")
            sys.exit(1)
        cmd_list(cfg, sys.argv[2])
    elif cmd == "stats":
        path_arg = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_stats(cfg, path_arg)
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    cli()
