#!/usr/bin/env python3
"""
skills-manager: 扫描和分析本机所有 skills 的分布、形式、状态。

使用说明:
  python3 scan_skills.py                          # 完整扫描并打印报表
  python3 scan_skills.py --json                   # 输出 JSON 格式
  python3 scan_skills.py --location claude        # 仅扫描指定位置

位置列表: agents, claude, workbuddy, custom
"""

import hashlib
import json
import os
import sys
from pathlib import Path


def expand_path(p: str) -> Path:
    return Path(os.path.expanduser(p))


SCAN_PATHS = {
    "agents": "~/.agents/skills",
    "claude": "~/.claude/skills",
    "workbuddy": "~/.workbuddy/skills",
    "custom": "~/repos/dxmanooskills",
}

LOCK_FILE = "~/.agents/.skill-lock.json"

LOCATION_LABELS = {
    "agents": ".agents 主仓库",
    "claude": "Claude Code",
    "workbuddy": "WorkBuddy",
    "custom": "自定义仓库",
}

# 形式图标
FORM_ICONS = {
    "directory": "📁",
    "symlink": "🔗",
    "git_repo": "📦",
    "broken": "💔",
}


def resolve_link_target(path: Path) -> str | None:
    if path.is_symlink():
        try:
            return str(path.resolve())
        except OSError:
            return "[BROKEN LINK]"
    return None


def file_hash(path: Path) -> str:
    """计算 SKILL.md 的 SHA256 用于内容比较"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def get_git_status(repo_path: Path) -> dict:
    """检查 Git 仓库的状态"""
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return {"is_git": False}

    result = {"is_git": True}
    try:
        import subprocess
        branch = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        result["branch"] = branch.stdout.strip() if branch.returncode == 0 else "unknown"

        status = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        result["dirty"] = bool(status.stdout.strip())

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
    返回 {location: {path, exists, skills: [...], git?}}
    """
    locations = {}
    if location:
        loc = location.lower()
        if loc in SCAN_PATHS:
            locations[loc] = SCAN_PATHS[loc]
        else:
            print(f"错误: 未知位置 '{location}'，可选: {', '.join(SCAN_PATHS.keys())}")
            sys.exit(1)
    else:
        locations = SCAN_PATHS.copy()

    result = {}

    for loc_name, raw_path in locations.items():
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
                # 检测是否指向 .agents
                agents_path = str(expand_path(SCAN_PATHS["agents"])).rstrip("/")
                info["points_to_agents"] = agents_path in link_target
            else:
                info["type"] = "directory"
                info["broken"] = False

            # 该 skill 同时在 .agents 中存在
            agents_skill = expand_path(SCAN_PATHS["agents"]) / item.name
            info["exists_in_agents"] = agents_skill.exists() or agents_skill.is_symlink()

            # SKILL.md
            skill_file = item / "SKILL.md"
            info["has_skill_md"] = skill_file.exists()
            info["skill_md_hash"] = file_hash(skill_file) if skill_file.exists() else ""

            try:
                stat = item.stat()
                info["modified"] = stat.st_mtime
            except OSError:
                info["modified"] = 0

            skills.append(info)

        entry = {"path": str(base), "exists": True, "skills": skills}

        if loc_name == "custom" and base.exists():
            git_info = get_git_status(base)
            if git_info["is_git"]:
                entry["git"] = git_info

        result[loc_name] = entry

    return result


def load_lock_file() -> dict | None:
    lock_path = expand_path(LOCK_FILE)
    if not lock_path.exists():
        return None
    try:
        with open(lock_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _fmt_mtime(ts: float) -> str:
    """ft 时间戳为简短日期"""
    import datetime
    if ts == 0:
        return "?"
    return datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")


def _is_standard_symlink(sk: dict) -> bool:
    """判断是否为标准 symlink（指向 .agents 或 custom repo）"""
    if sk.get("type") != "symlink":
        return False
    if sk.get("broken"):
        return False
    target = sk.get("target", "")
    agents_path = str(expand_path(SCAN_PATHS["agents"])).rstrip("/")
    custom_path = str(expand_path(SCAN_PATHS["custom"])).rstrip("/")
    return agents_path in target or custom_path in target


def format_scan_report(scan_data: dict, lock_data: dict | None = None) -> str:
    """生成带形式标识和冲突检测的报表"""
    lines = []
    separator = "─" * 58

    lines.append("┌" + separator + "┐")
    total_all = sum(len(e["skills"]) for e in scan_data.values() if e["exists"])
    active_locs = sum(1 for e in scan_data.values() if e["exists"])
    lines.append(f"│  skills-manager  发现 {total_all} skills × {active_locs} 个位置")
    lines.append("└" + separator + "┘")
    lines.append("")

    for loc_name, entry in scan_data.items():
        if not entry["exists"]:
            lines.append(f"  [{loc_name}] 路径不存在: {entry['path']}")
            lines.append("")
            continue

        label = LOCATION_LABELS.get(loc_name, loc_name)
        skills = entry["skills"]
        path_short = entry["path"].replace(os.path.expanduser("~"), "~")
        lines.append(f"  {label}  ({len(skills)})    {path_short}")

        if loc_name == "custom" and entry.get("git"):
            g = entry["git"]
            git_info = f"分支: {g.get('branch', '?')}"
            if g.get("dirty"):
                git_info += " [有未提交变更]"
            if g.get("ahead", 0) > 0:
                git_info += f" [领先远程 {g['ahead']}]"
            if g.get("behind", 0) > 0:
                git_info += f" [落后远程 {g['behind']}]"
            lines.append(f"             {git_info}")

        lines.append("  " + "─" * 55)

        for sk in skills:
            icon = FORM_ICONS.get(sk["type"], "?")
            if sk.get("broken"):
                icon = FORM_ICONS["broken"]

            name = sk["name"]
            md_flag = "✓" if sk.get("has_skill_md") else "✗"

            # 构建形式说明
            if sk.get("broken"):
                form_desc = "→ [断裂!] " + sk.get("target", "")
            elif sk["type"] == "symlink":
                target = sk.get("target", "")
                target_short = target.replace(os.path.expanduser("~"), "~")
                form_desc = f"→ {target_short}"
            else:
                form_desc = "独立目录"

            # 是否标准（custom 是 git 源码仓库，目录是正常的）
            anomaly = ""
            if loc_name not in ("agents", "custom") and sk["type"] == "directory":
                anomaly = " ⚠ 非标准 (应为 symlink)"

            if sk.get("exists_in_agents") and loc_name not in ("agents", "custom"):
                if sk["type"] == "directory":
                    anomaly += " ⚡同名冲突(与 agents)"

            lines.append(f"  {icon} {md_flag} {name:<28} {form_desc}{anomaly}")

        # 异常汇总行
        anomalies_here = [sk for sk in skills
                          if (loc_name not in ("agents", "custom") and sk["type"] == "directory")
                          or sk.get("broken")]
        if anomalies_here:
            lines.append(f"     ── 本位置有 {len(anomalies_here)} 个异常 ──")
        lines.append("")

    # ── 跨位置冲突检测 ──
    conflicts = find_conflicts(scan_data)
    if conflicts:
        lines.append("  ╔══ 冲突检测 ═══════════════════════════════════════╗")
        lines.append("  ║  以下 skill 在多个位置以不同形式/内容存在:      ║")
        lines.append("  ╚═══════════════════════════════════════════════════╝")
        lines.append("")
        for name, entries in conflicts.items():
            lines.append(f"  ⚡ {name}")
            for loc_name, sk in entries:
                icon = FORM_ICONS.get(sk["type"], "?")
                loc_label = LOCATION_LABELS.get(loc_name, loc_name)
                h = sk.get("skill_md_hash", "")
                hash_info = f"  SKILL.md: [{h}]" if h else "  无 SKILL.md"
                lines.append(f"     {icon} {loc_label:<18} {hash_info}")
            lines.append("")

    # ── 锁文件信息 ──
    if lock_data:
        lock_v = lock_data.get("version", "?")
        lock_count = len(lock_data.get("skills", {}))
        lines.append(f"  🔒 .skill-lock.json v{lock_v} | {lock_count} 个 skill 版本追踪")
        lines.append("")

    lines.append(separator)
    return "\n".join(lines)


def find_conflicts(scan_data: dict) -> dict:
    """
    检测同名 skill 在不同位置的冲突。
    返回 {skill_name: [(location, skill_info), ...], ...}
    冲突条件: 同名且有一个不是 symlink to agents
    """
    # 收集所有 skill: name -> [(loc, info), ...]
    all_skills: dict[str, list] = {}
    for loc_name, entry in scan_data.items():
        if not entry["exists"]:
            continue
        for sk in entry["skills"]:
            name = sk["name"]
            if name not in all_skills:
                all_skills[name] = []
            all_skills[name].append((loc_name, sk))

    conflicts = {}
    for name, entries in all_skills.items():
        if len(entries) < 2:
            continue

        # 检查是否有非标准条目（不是 symlink to agents 的）
        has_non_standard = any(
            sk.get("type") != "symlink"
            for _, sk in entries
        )
        if not has_non_standard:
            continue

        # 检查是否有不同 hash
        hashes = {sk.get("skill_md_hash", "") for _, sk in entries if sk.get("has_skill_md")}
        if len(hashes) <= 1:
            continue

        conflicts[name] = entries

    return conflicts


def main():
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
