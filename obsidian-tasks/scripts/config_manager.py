#!/usr/bin/env python3
"""
config_manager.py — Obsidian Tasks Skill 配置管理器

用法:
  python3 config_manager.py show
  python3 config_manager.py set <key> <value>
  python3 config_manager.py init
  python3 config_manager.py reset
"""

import sys
import os
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config" / "defaults.yaml"

FIELDS_META = {
    "vault_path": {
        "question": "Obsidian vault 根目录的绝对路径是什么？\n例如：/Users/你的用户名/Documents/MyVault",
        "example": "/Users/guo/Obsidian/Vault"
    },
    "task_format": {
        "question": "任务格式偏好？\n  emoji   — Emoji 符号格式（如 📅 2026-05-10）\n  dataview — Dataview 格式（如 [due:: 2026-05-10]）",
        "example": "emoji",
        "options": ["emoji", "dataview"]
    },
    "default_inbox_file": {
        "question": "新建任务默认写入哪个文件？\n输入相对于 vault 根目录的路径",
        "example": "Inbox.md"
    },
    "default_query_dir": {
        "question": "Query 看板文件默认生成到哪个目录？\n输入相对于 vault 根目录的路径（如不存在会自动创建）",
        "example": "Dashboards"
    },
}


def load_config() -> dict:
    """加载配置文件，返回字典。文件不存在则返回空字典。"""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(cfg: dict) -> None:
    """保存配置到 YAML 文件。"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def show_config() -> None:
    """展示当前配置。"""
    cfg = load_config()
    if not cfg:
        print("⚠️  配置文件不存在，请先运行 init 进行初始化。")
        return

    print("=" * 50)
    print("📋 Obsidian Tasks Skill 当前配置")
    print("=" * 50)

    keys_display = [
        ("vault_path", "Vault 路径"),
        ("task_format", "任务格式"),
        ("default_inbox_file", "默认 Inbox 文件"),
        ("default_query_dir", "默认 Query 目录"),
        ("date_format", "日期格式"),
        ("auto_add_created_date", "自动添加创建日期"),
        ("first_run_done", "已完成首次配置"),
    ]

    for key, label in keys_display:
        val = cfg.get(key, "")
        # 敏感提示
        if key == "vault_path" and val:
            val = val if os.path.exists(val) else f"{val} ⚠️ 路径不存在"
        marker = "✅" if cfg.get("first_run_done") and key == "first_run_done" else ""
        print(f"  {label}: {val} {marker}")

    print("=" * 50)


def set_value(key: str, value: str) -> None:
    """设置单个配置项。"""
    cfg = load_config()

    # 布尔值转换
    if value.lower() in ("true", "yes", "1"):
        value = True
    elif value.lower() in ("false", "no", "0"):
        value = False

    cfg[key] = value
    save_config(cfg)
    print(f"✅ 已更新：{key} = {value}")


def init_config(interactive: bool = True) -> dict:
    """初始化配置（交互式询问）。返回配置字典。"""
    cfg = load_config()
    if cfg.get("first_run_done"):
        print("✅ 配置已完成。如需重新初始化，请先运行 reset。")
        return cfg

    print("\n🔧 Obsidian Tasks Skill 首次配置\n")
    print("请回答以下问题（输入后按回车）：\n")

    answers = {}
    for key, meta in FIELDS_META.items():
        print(f"--- {meta['question']} ---")
        if "example" in meta:
            print(f"  示例：{meta['example']}")
        val = input("> ").strip()
        if not val:
            val = meta.get("example", "")
        answers[key] = val
        print()

    # 写入默认值（如果用户未修改）
    default_cfg = {
        "vault_path": "",
        "task_format": "emoji",
        "default_inbox_file": "Inbox.md",
        "default_query_dir": "Dashboards",
        "date_format": "YYYY-MM-DD",
        "auto_add_created_date": True,
        "first_run_done": False,
    }
    for k, v in default_cfg.items():
        if k not in cfg:
            cfg[k] = v

    cfg.update(answers)
    cfg["first_run_done"] = True

    save_config(cfg)
    print("\n✅ 配置已保存！当前配置如下：\n")
    show_config()
    return cfg


def reset_config() -> None:
    """重置配置（保留文件但清空关键字段）。"""
    default_cfg = {
        "vault_path": "",
        "task_format": "emoji",
        "default_inbox_file": "Inbox.md",
        "default_query_dir": "Dashboards",
        "date_format": "YYYY-MM-DD",
        "auto_add_created_date": True,
        "first_run_done": False,
    }
    save_config(default_cfg)
    print("🔄 配置已重置。请运行 init 重新配置。")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "show":
        show_config()
    elif cmd == "set":
        if len(sys.argv) < 4:
            print("用法: config_manager.py set <key> <value>")
            sys.exit(1)
        set_value(sys.argv[2], sys.argv[3])
    elif cmd == "init":
        init_config(interactive=True)
    elif cmd == "reset":
        reset_config()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
