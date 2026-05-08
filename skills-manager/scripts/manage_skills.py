#!/usr/bin/env python3
"""
skills-manager: 同步、链接管理、版本管理和健康检查。

使用说明:
  python3 manage_skills.py health        # 健康检查
  python3 manage_skills.py sync          # 同步所有终端
  python3 manage_skills.py sync claude   # 仅同步 Claude Code
  python3 manage_skills.py link <name>   # 为 skill 创建 claude 符号链接
  python3 manage_skills.py version       # 版本信息
  python3 manage_skills.py update        # 更新所有 skills
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def expand_path(p: str) -> Path:
    return Path(os.path.expanduser(p))


# 路径定义
AGENTS_DIR = expand_path("~/.agents/skills")
CLAUDE_DIR = expand_path("~/.claude/skills")
WORKBUDDY_DIR = expand_path("~/.workbuddy/skills")
CUSTOM_REPO = expand_path("~/repos/dxmanooskills")
LOCK_FILE = expand_path("~/.agents/.skill-lock.json")


# ── 辅助 ──────────────────────────────────────────────

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> str:
    """运行命令并返回 stdout（忽略错误）"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def info(msg: str):
    print(f"  • {msg}")


def ok(msg: str):
    print(f"  ✓ {msg}")


def warn(msg: str):
    print(f"  ⚠ {msg}")


def err(msg: str):
    print(f"  ✗ {msg}")


# ── 健康检查 ──────────────────────────────────────────

def cmd_health():
    print("═══ 健康检查 ═══\n")

    issues = 0

    # 1. 检查各目录是否存在
    for label, path in [(".agents", AGENTS_DIR), ("Claude Code", CLAUDE_DIR),
                         ("WorkBuddy", WORKBUDDY_DIR), ("自定义仓库", CUSTOM_REPO)]:
        if path.exists():
            ok(f"{label}: {path}")
        else:
            warn(f"{label}: 路径不存在 ({path})")
            issues += 1

    print()

    # 2. 检查断裂链接
    broken = []
    for label, base in [("Claude Code", CLAUDE_DIR), ("WorkBuddy", WORKBUDDY_DIR)]:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.is_symlink() and not item.exists():
                broken.append((label, item.name, str(item.resolve())))

    if broken:
        warn(f"发现 {len(broken)} 个断裂链接:")
        for label, name, target in broken:
            warn(f"  {label}/{name} -> {target} [断裂]")
        issues += len(broken)
    else:
        ok("所有符号链接有效")

    # 3. 检查 SKILL.md 缺失
    no_md = []
    for label, base in [(".agents", AGENTS_DIR), ("WorkBuddy", WORKBUDDY_DIR),
                         ("自定义仓库", CUSTOM_REPO)]:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir() or item.is_symlink():
                if not (item / "SKILL.md").exists():
                    no_md.append(f"{label}/{item.name}")

    if no_md:
        warn(f"{len(no_md)} 个 skill 缺少 SKILL.md")
        for n in no_md:
            warn(f"  {n}")
    else:
        ok("所有 skill 都有 SKILL.md")

    # 4. 检查重复
    names_agents = {p.name for p in AGENTS_DIR.iterdir() if not p.name.startswith(".")} if AGENTS_DIR.exists() else set()
    names_claude = {p.name for p in CLAUDE_DIR.iterdir() if not p.name.startswith(".")} if CLAUDE_DIR.exists() else set()
    names_wb = {p.name for p in WORKBUDDY_DIR.iterdir() if not p.name.startswith(".")} if WORKBUDDY_DIR.exists() else set()

    print()
    overlaps = names_agents & names_wb
    if overlaps:
        warn("agents 与 workbuddy 之间存在同名 skill（可能冲突）:")
        for n in sorted(overlaps):
            warn(f"  {n}")
    else:
        ok("无跨目录 skill 名称冲突")

    # 5. Git 状态
    if CUSTOM_REPO.exists():
        print()
        branch = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--abbrev-ref", "HEAD"])
        dirty = run(["git", "-C", str(CUSTOM_REPO), "status", "--porcelain"])
        if dirty:
            warn(f"自定义仓库 ({branch}) 有未提交变更")
        else:
            ok(f"自定义仓库 ({branch}) 干净")

    print(f"\n═══ 完成: {issues} 个问题 ═══")


# ── 同步 ──────────────────────────────────────────────

def cmd_sync(target: str | None = None):
    print("═══ 同步 skills ═══\n")

    # 确保源存在
    if not AGENTS_DIR.exists():
        err(".agents/skills 目录不存在，无法作为源")
        return

    targets = []
    if target == "claude" or target is None:
        targets.append(("Claude Code", CLAUDE_DIR, AGENTS_DIR))

    for label, link_dir, source_dir in targets:
        if not link_dir.exists():
            warn(f"{label} 目录不存在，跳过")
            continue

        ok(f"检查 {label}...")
        synced = 0
        for skill_dir in source_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            link_path = link_dir / skill_dir.name
            expected_target = str(skill_dir.resolve())
            if link_path.is_symlink():
                existing = str(link_path.resolve())
                if existing == expected_target:
                    continue
                link_path.unlink()
            elif link_path.exists():
                # 同名文件/目录但不是链接 — 跳过
                continue

            link_path.symlink_to(expected_target)
            synced += 1
            ok(f"  链接 {skill_dir.name} -> {label}")

        if synced == 0:
            info(f"{label} 已是最新，无需同步")

    print("\n同步完成")


# ── 创建/修复链接 ────────────────────────────────────

def cmd_link(name: str):
    """为指定 skill 创建或修复符号链接"""
    # 搜索源
    source = None
    for src_dir in [CUSTOM_REPO, AGENTS_DIR]:
        p = src_dir / name
        if (p / "SKILL.md").exists() or p.is_dir():
            source = p
            break
    if not source:
        err(f"未找到 skill '{name}'")
        return

    # 链接到 Claude
    claude_link = CLAUDE_DIR / name
    if claude_link.is_symlink():
        claude_link.unlink()
    claude_link.symlink_to(str(source.resolve()))
    ok(f"Claude Code: {claude_link} -> {source.resolve()}")

    # 链接到 WorkBuddy
    wb_link = WORKBUDDY_DIR / name
    if wb_link.is_symlink():
        wb_link.unlink()
    elif wb_link.exists():
        warn(f"WorkBuddy 已有同名目录 {wb_link}，跳过")
        return
    wb_link.symlink_to(str(source.resolve()))
    ok(f"WorkBuddy: {wb_link} -> {source.resolve()}")


# ── 版本信息 ──────────────────────────────────────────

def cmd_version():
    print("═══ 版本信息 ═══\n")

    # .skill-lock.json
    if LOCK_FILE.exists():
        with open(LOCK_FILE) as f:
            lock = json.load(f)
        print(f"🔒 .skill-lock.json v{lock.get('version', '?')}")
        skills_locked = lock.get("skills", {})
        print(f"   记录 {len(skills_locked)} 个 skill\n")

        # 显示所有锁定的 skill
        for name, info in sorted(skills_locked.items()):
            source = info.get("source", "?")
            updated = info.get("updatedAt", "?")[:10]
            print(f"   {name:<25} {source:<35} {updated}")
    else:
        warn("未找到 .skill-lock.json")

    # 自定义仓库 Git 版本
    print()
    if CUSTOM_REPO.exists():
        branch = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--abbrev-ref", "HEAD"])
        commit = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--short", "HEAD"])
        msg = run(["git", "-C", str(CUSTOM_REPO), "log", "--oneline", "-1"])
        print(f"📦 自定义仓库 ({branch}):")
        print(f"   {commit} {msg}")
    else:
        warn("自定义仓库不存在")

    # 各目录 skill 数量
    print()
    for label, path in [(".agents", AGENTS_DIR), ("Claude Code", CLAUDE_DIR),
                         ("WorkBuddy", WORKBUDDY_DIR)]:
        if path.exists():
            count = len([p for p in path.iterdir() if not p.name.startswith(".")])
            print(f"   {label:<15} {count} skills")


# ── 更新 ──────────────────────────────────────────────

def cmd_update():
    print("═══ 更新 skills ═══\n")

    # 1. npx skills update
    info("检查 npx skills 更新...")
    result = run(["npx", "skills", "check"])
    print(f"   {result}")
    result = run(["npx", "skills", "update"])
    print(f"   {result}")

    # 2. 自定义仓库
    print()
    if CUSTOM_REPO.exists():
        info("更新自定义仓库...")
        branch = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--abbrev-ref", "HEAD"])
        run(["git", "-C", str(CUSTOM_REPO), "fetch", "--all"])
        behind = run(["git", "-C", str(CUSTOM_REPO), "rev-list", "--count", "HEAD..origin/HEAD", "--"])
        if behind.strip() and int(behind) > 0:
            run(["git", "-C", str(CUSTOM_REPO), "pull"])
            ok(f"自定义仓库已更新（落后 {behind} 个提交）")
        else:
            info("自定义仓库已是最新")
    else:
        warn("自定义仓库不存在，跳过")

    # 3. 同步链接
    print()
    cmd_sync(None)

    print("\n更新完成")


# ── 主入口 ────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 manage_skills.py health       # 健康检查")
        print("  python3 manage_skills.py sync [loc]   # 同步（可选: claude）")
        print("  python3 manage_skills.py link <name>  # 为 skill 创建链接")
        print("  python3 manage_skills.py version      # 版本信息")
        print("  python3 manage_skills.py update       # 更新所有 skills")
        return

    cmd = sys.argv[1]

    if cmd == "health":
        cmd_health()
    elif cmd == "sync":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_sync(target)
    elif cmd == "link":
        if len(sys.argv) < 3:
            err("请指定 skill 名称: python3 manage_skills.py link <name>")
            return
        cmd_link(sys.argv[2])
    elif cmd == "version":
        cmd_version()
    elif cmd == "update":
        cmd_update()
    else:
        err(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
