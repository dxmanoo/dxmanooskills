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


def _build_type_stats(scan_data: dict) -> dict:
    """统计各位置按 type 分类的数量"""
    stats = {}
    for loc_name, entry in scan_data.items():
        if not entry["exists"]:
            continue
        counts = {"directory": 0, "symlink": 0, "broken": 0}
        for sk in entry["skills"]:
            t = sk.get("type", "directory")
            if sk.get("broken"):
                t = "broken"
            counts[t] = counts.get(t, 0) + 1
        stats[loc_name] = counts
    return stats


def _build_location_matrix(scan_data: dict) -> dict:
    """
    构建 {skill_name: {loc_name: {type, hash, exists_in_agents}}, ...}
    用于交叉对照
    """
    matrix: dict[str, dict] = {}
    for loc_name, entry in scan_data.items():
        if not entry["exists"]:
            continue
        for sk in entry["skills"]:
            name = sk["name"]
            if name not in matrix:
                matrix[name] = {}
            matrix[name][loc_name] = {
                "type": sk.get("type", "?"),
                "broken": sk.get("broken", False),
                "hash": sk.get("skill_md_hash", ""),
                "has_md": sk.get("has_skill_md", False),
            }
    return matrix


BOLD = "\033[1m"
RESET = "\033[0m"


def format_scan_report(scan_data: dict, lock_data: dict | None = None) -> str:
    """生成管理友好的多视角扫描报表"""
    lines = []
    H = "─" * 60
    active_locs = [(ln, e) for ln, e in scan_data.items() if e["exists"]]
    total_all = sum(len(e["skills"]) for _, e in active_locs)

    loc_order = ["agents", "claude", "workbuddy", "custom"]
    labels = {
        "agents": ".agents 主仓库",
        "claude": "Claude Code",
        "workbuddy": "WorkBuddy",
        "custom": "自定义仓库",
    }
    short_labels = {"agents": "agents", "claude": "claude", "workbuddy": "wb", "custom": "custom"}

    # ── HEADER ──
    lines.append("")
    lines.append(f"  {'═' * 56}")
    lines.append(f"  ║  skills-manager  扫描报告")
    lines.append(f"  ║  {total_all} skills × {len(active_locs)} 个位置")
    lines.append(f"  {'═' * 56}")
    lines.append("")

    # ════════════════════════════════════════════
    #  SECTION 1: 分布一览表
    # ════════════════════════════════════════════
    lines.append(f"  ▸ 分布一览")
    lines.append(f"  {H}")
    stats = _build_type_stats(scan_data)
    # Header row
    lines.append(f"  {'位置':<20} {'总计':>6} {'📁目录':>8} {'🔗链接':>8} {'路径':>25}")
    lines.append(f"  {'─'*19} {'─'*6} {'─'*8} {'─'*8} {'─'*25}")
    for loc in loc_order:
        if loc not in dict(active_locs):
            continue
        entry = dict(active_locs)[loc] if loc in dict(active_locs) else None
        # 重新获取 entry
        entry = None
        for ln, e in active_locs:
            if ln == loc:
                entry = e
                break
        if entry is None:
            continue

        s = stats.get(loc, {})
        total_loc = len(entry["skills"])
        dirs = s.get("directory", 0)
        links = s.get("symlink", 0)
        broken = s.get("broken", 0)
        path_short = entry["path"].replace(os.path.expanduser("~"), "~")
        broken_str = f" (+{broken}💔)" if broken else ""
        lines.append(f"  {labels.get(loc, loc):<20} {total_loc:>4}{broken_str}    {dirs:>4}     {links:>4}   {path_short}")

        if loc == "custom" and entry.get("git"):
            g = entry["git"]
            parts = []
            if g.get("dirty"):
                parts.append("有未提交变更")
            if g.get("ahead", 0) > 0:
                parts.append(f"领先远程 {g['ahead']}")
            if g.get("behind", 0) > 0:
                parts.append(f"落后远程 {g['behind']}")
            if parts:
                lines.append(f"  {'':<20} {'':>6}   Git: {', '.join(parts)}")
    lines.append("")

    # ════════════════════════════════════════════
    #  SECTION 2: 详细清单（按位置）
    # ════════════════════════════════════════════
    lines.append(f"  ▸ 详细清单（按位置）")
    lines.append(f"  {H}")

    for loc in loc_order:
        entry = None
        for ln, e in active_locs:
            if ln == loc:
                entry = e
                break
        if entry is None:
            continue

        skills = entry["skills"]
        label = labels.get(loc, loc)
        path_short = entry["path"].replace(os.path.expanduser("~"), "~")
        lines.append("")
        lines.append(f"  ╓── {label}  ({len(skills)}) ── {path_short}")
        if loc == "custom" and entry.get("git"):
            g = entry["git"]
            lines.append(f"  ║  Git: {g.get('branch', '?')}"
                         f"{'  [dirty]' if g.get('dirty') else ''}"
                         f"{'  [ahead ' + str(g['ahead']) + ']' if g.get('ahead', 0) > 0 else ''}"
                         f"{'  [behind ' + str(g['behind']) + ']' if g.get('behind', 0) > 0 else ''}")

        # 分组: 目录 / symlink / broken
        dir_skills = [s for s in skills if s["type"] == "directory" and not s.get("broken")]
        link_skills = [s for s in skills if s["type"] == "symlink" and not s.get("broken")]
        broken_skills = [s for s in skills if s.get("broken")]

        if dir_skills:
            lines.append(f"  ║  ── 📁 独立目录 ({len(dir_skills)}) ──")
            for sk in dir_skills:
                mark = ""
                if loc not in ("agents", "custom"):
                    mark = "  ← 非标准，应为 symlink"
                elif sk.get("exists_in_agents") and loc != "agents":
                    mark = "  ← agents 也有此 skill"
                lines.append(f"  ║    {sk['name']:<30}{mark}")
        if link_skills:
            lines.append(f"  ║  ── 🔗 符号链接 ({len(link_skills)}) ──")
            for sk in link_skills:
                target = sk.get("target", "").replace(os.path.expanduser("~"), "~")
                lines.append(f"  ║    {sk['name']:<30} → {target}")
        if broken_skills:
            lines.append(f"  ║  ── 💔 断裂链接 ({len(broken_skills)}) ──")
            for sk in broken_skills:
                lines.append(f"  ║    {sk['name']:<30} → [断裂] {sk.get('target', '?')}")
        lines.append(f"  ╙──")

    # ════════════════════════════════════════════
    #  SECTION 3: 交叉对照表
    # ════════════════════════════════════════════
    lines.append("")
    lines.append(f"  ▸ 交叉对照（同名 skill 跨位置分布）")
    lines.append(f"  {H}")

    matrix = _build_location_matrix(scan_data)
    multi_loc = {n: locs for n, locs in sorted(matrix.items()) if len(locs) > 1}
    if multi_loc:
        # Header
        loc_keys = [l for l in loc_order if l in dict(active_locs)]
        lines.append(f"  {'skill':<28} " + "  ".join(f"{short_labels.get(l,l):>8}" for l in loc_keys))
        lines.append(f"  {'─'*27}  " + "  ".join("─" * 8 for _ in loc_keys))

        for sname, locs_dict in multi_loc.items():
            row = f"  {sname:<28}"
            for loc in loc_keys:
                info = locs_dict.get(loc)
                if not info:
                    row += f"  {'─':>8}"
                elif info["broken"]:
                    row += f"  {'💔断裂':>8}"
                elif info["type"] == "symlink":
                    row += f"  {'🔗链接':>8}"
                else:
                    # directory — show first 4 hash chars
                    h = info.get("hash", "")[:4]
                    row += f"  {'📁'+h:>8}" if h else "  {'📁':>8}"
            lines.append(row)

        # 图例
        lines.append(f"  {'':28}  📁=目录  🔗=链接  💔=断裂  ─=不存在")
    else:
        lines.append("  （无跨位置同名 skill）")
    lines.append("")

    # ════════════════════════════════════════════
    #  SECTION 4: 冲突与问题
    # ════════════════════════════════════════════
    issues: list[str] = []

    # 4a. 断裂链接
    for loc, entry in active_locs:
        for sk in entry["skills"]:
            if sk.get("broken"):
                issues.append(f"  💔 {labels.get(loc, loc)}/{sk['name']} 链接断裂 → {sk.get('target','')}")

    # 4b. 非标准存在形式
    for loc, entry in active_locs:
        if loc in ("agents", "custom"):
            continue
        for sk in entry["skills"]:
            if sk["type"] == "directory":
                issues.append(f"  ⚠ {labels.get(loc, loc)}/{sk['name']} 是独立目录，应为 symlink")

    # 4c. 同名冲突 (hash 不同)
    conflicts = find_conflicts(scan_data)
    for cname, entries in conflicts.items():
        parts = []
        for loc_name, sk in entries:
            loc_label = labels.get(loc_name, loc_name)
            h = sk.get("skill_md_hash", "?")[:8]
            icon = "💔" if sk.get("broken") else FORM_ICONS.get(sk["type"], "?")
            parts.append(f"{icon} {loc_label}[{h}]")
        issues.append(f"  ⚡ {cname}: " + "  vs  ".join(parts))

    # 4d. 无 SKILL.md
    for loc, entry in active_locs:
        for sk in entry["skills"]:
            if not sk.get("has_skill_md"):
                issues.append(f"  ✗ {labels.get(loc, loc)}/{sk['name']} 缺少 SKILL.md")

    if issues:
        lines.append(f"  ▸ 待处理问题 ({len(issues)} 项)")
        lines.append(f"  {H}")
        for issue in issues:
            lines.append(issue)
        lines.append("")
    else:
        lines.append(f"  ▸ 待处理问题")
        lines.append(f"  {H}")
        lines.append("  （无待处理问题）")
        lines.append("")

    # ── FOOTER ──
    if lock_data:
        lock_v = lock_data.get("version", "?")
        lock_count = len(lock_data.get("skills", {}))
        lines.append(f"  🔒 .skill-lock.json v{lock_v} | {lock_count} 个 skill 版本追踪")
        lines.append("")

    lines.append(f"  {'─' * 56}")
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
