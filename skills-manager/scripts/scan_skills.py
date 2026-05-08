#!/usr/bin/env python3
"""
skills-manager: 扫描和分析本机所有 skills 的分布、形式、状态。

使用说明:
  python3 scan_skills.py                     # 完整扫描并打印报表
  python3 scan_skills.py --json              # 输出 JSON 格式
  python3 scan_skills.py --location claude   # 仅扫描指定位置

位置列表: agents, claude, workbuddy, custom
"""

import json
import os
import sys
from pathlib import Path


def expand_path(p: str) -> Path:
    """展开 ~ 为完整路径"""
    return Path(os.path.expanduser(p))


# 默认扫描路径（与 config.json 对齐）
SCAN_PATHS = {
    "agents": "~/.agents/skills",
    "claude": "~/.claude/skills",
    "workbuddy": "~/.workbuddy/skills",
    "custom": "~/repos/dxmanooskills",
}

LOCK_FILE = "~/.agents/.skill-lock.json"
CUSTOM_REPO = "~/repos/dxmanooskills"


def resolve_link_target(path: Path) -> str | None:
    """如果是符号链接，返回目标路径；否则返回 None"""
    if path.is_symlink():
        try:
            return str(path.resolve())
        except OSError:
            return "[BROKEN LINK]"
    return None


def get_git_status(repo_path: Path) -> dict:
    """检查 Git 仓库的状态"""
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return {"is_git": False}

    result = {"is_git": True}
    try:
        import subprocess
        # 当前分支
        branch = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        result["branch"] = branch.stdout.strip() if branch.returncode == 0 else "unknown"

        # 是否有未提交变更
        status = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        result["dirty"] = bool(status.stdout.strip())

        # 与 remote 的关系
        subprocess.run(
            ["git", "-C", str(repo_path), "fetch", "--all"],
            capture_output=True, timeout=10
        )
        behind = subprocess.run(
            ["git", "-C", str(repo_path), "rev-list", "--count", "HEAD..origin/HEAD", "--"],
            capture_output=True, text=True, timeout=5
        )
        ahead = subprocess.run(
            ["git", "-C", str(repo_path), "rev-list", "--count", "origin/HEAD..HEAD", "--"],
            capture_output=True, text=True, timeout=5
        )
        result["behind"] = int(behind.stdout.strip() or 0)
        result["ahead"] = int(ahead.stdout.strip() or 0)
    except Exception as e:
        result["error"] = str(e)
    return result


def scan_skills(location: str | None = None) -> dict:
    """
    扫描指定位置（或所有位置）的 skills。
    返回 {location: [skill_info, ...], ...}
    """
    locations_to_scan = {}
    if location:
        loc = location.lower()
        if loc in SCAN_PATHS:
            locations_to_scan[loc] = SCAN_PATHS[loc]
        else:
            print(f"错误: 未知位置 '{location}'，可选: {', '.join(SCAN_PATHS.keys())}")
            sys.exit(1)
    else:
        locations_to_scan = SCAN_PATHS.copy()

    result = {}

    for loc_name, raw_path in locations_to_scan.items():
        base = expand_path(raw_path)
        if not base.exists():
            result[loc_name] = {"path": str(base), "exists": False, "skills": []}
            continue

        skills = []
        for item in sorted(base.iterdir()):
            if not item.is_dir() and not item.is_symlink():
                continue
            if item.name.startswith("."):
                continue

            info = {"name": item.name}
            link_target = resolve_link_target(item)
            if link_target:
                info["type"] = "symlink"
                info["target"] = link_target
                info["broken"] = not item.exists()
            else:
                info["type"] = "directory"

            # 检查 SKILL.md
            skill_file = item / "SKILL.md"
            info["has_skill_md"] = skill_file.exists()

            # 获取文件大小和修改时间
            try:
                stat = item.stat()
                info["modified"] = stat.st_mtime
            except OSError:
                info["modified"] = 0

            skills.append(info)

        entry = {"path": str(base), "exists": True, "skills": skills}

        # 对 custom 仓库额外检查 Git 状态
        if loc_name == "custom" and base.exists():
            git_info = get_git_status(base)
            if git_info["is_git"]:
                entry["git"] = git_info

        result[loc_name] = entry

    return result


def load_lock_file() -> dict | None:
    """加载 .skill-lock.json 版本锁定信息"""
    lock_path = expand_path(LOCK_FILE)
    if not lock_path.exists():
        return None
    try:
        with open(lock_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def format_scan_report(scan_data: dict, lock_data: dict | None = None) -> str:
    """格式化为可读报表"""
    lines = []
    lines.append("=" * 60)
    lines.append("  SKILLS MANAGER — 扫描报告")
    lines.append("=" * 60)
    lines.append("")

    total_all = 0

    for loc_name, entry in scan_data.items():
        if not entry["exists"]:
            lines.append(f"[{loc_name}] 路径不存在: {entry['path']}")
            lines.append("")
            continue

        loc_label = {
            "agents": ".agents 主仓库",
            "claude": "Claude Code",
            "workbuddy": "WorkBuddy",
            "custom": "自定义仓库",
        }.get(loc_name, loc_name)

        skills = entry["skills"]
        total_all += len(skills)
        lines.append(f"── {loc_label} ({len(skills)} skills) ──")
        lines.append(f"   路径: {entry['path']}")

        if loc_name == "custom" and entry.get("git"):
            g = entry["git"]
            lines.append(f"   Git 分支: {g.get('branch', 'N/A')}")
            status_parts = []
            if g.get("dirty"):
                status_parts.append("有未提交变更")
            if g.get("ahead", 0) > 0:
                status_parts.append(f"比远程领先 {g['ahead']} 个提交")
            if g.get("behind", 0) > 0:
                status_parts.append(f"比远程落后 {g['behind']} 个提交")
            if status_parts:
                lines.append(f"   Git 状态: {', '.join(status_parts)}")

        lines.append("")
        for sk in skills:
            marker = ""
            if sk.get("broken"):
                marker = " [断裂!]"
            elif sk["type"] == "symlink":
                marker = f" -> {sk['target']}"
            has_md = "✓" if sk.get("has_skill_md") else "✗"
            lines.append(f"   {has_md} {sk['name']}{marker}")

        lines.append("")

    # 汇总
    lines.append("─" * 40)
    lines.append(f"  总计: {total_all} skills 在 {sum(1 for e in scan_data.values() if e['exists'])} 个位置")
    lines.append("")

    # 添加 lock 信息
    if lock_data:
        lines.append(f"  🔒 .skill-lock.json v{lock_data.get('version', '?')}")
        lines.append(f"     记录 {len(lock_data.get('skills', {}))} 个 skill 版本")

    # 扫描断裂链接
    broken = []
    for entry in scan_data.values():
        for sk in entry.get("skills", []):
            if sk.get("broken"):
                broken.append(sk["name"])
    if broken:
        lines.append(f"  ⚠️ 发现 {len(broken)} 个断裂链接: {', '.join(broken)}")

    # 扫描缺少 SKILL.md 的
    no_md = []
    for entry in scan_data.values():
        for sk in entry.get("skills", []):
            if not sk.get("has_skill_md"):
                no_md.append(f"{sk['name']}")
    if no_md:
        lines.append(f"  ⚠️ {len(no_md)} 个 skill 缺少 SKILL.md")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    # 解析参数
    location = None
    output_json = False
    for arg in sys.argv[1:]:
        if arg == "--json":
            output_json = True
        elif arg.startswith("--location="):
            location = arg.split("=", 1)[1]
        elif arg.startswith("--loc="):
            location = arg.split("=", 1)[1]

    scan_data = scan_skills(location)
    lock_data = load_lock_file()

    if output_json:
        output = {"scan": scan_data}
        if lock_data:
            output["lock_file"] = lock_data
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_scan_report(scan_data, lock_data))


if __name__ == "__main__":
    main()
