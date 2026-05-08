#!/usr/bin/env python3
"""
skills-manager: 同步、整理、版本管理和健康检查。

核心策略: .agents/skills/ 为主仓库（canonical source），
其他终端（claude, workbuddy）仅做符号链接。

使用说明:
  python3 manage_skills.py health             # 健康检查
  python3 manage_skills.py sync [loc]         # 同步（默认所有）
  python3 manage_skills.py organize           # 整理: 扫描冲突 + 修复
  python3 manage_skills.py link <name>        # 为 skill 创建跨终端链接
  python3 manage_skills.py version            # 版本信息
  python3 manage_skills.py update             # 更新所有 skills
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def expand_path(p: str) -> Path:
    return Path(os.path.expanduser(p))


AGENTS_DIR = expand_path("~/.agents/skills")
CLAUDE_DIR = expand_path("~/.claude/skills")
WORKBUDDY_DIR = expand_path("~/.workbuddy/skills")
CUSTOM_REPO = expand_path("~/repos/dxmanooskills")
LOCK_FILE = expand_path("~/.agents/.skill-lock.json")

LOCATION_LABELS = {
    AGENTS_DIR: ".agents 主仓库",
    CLAUDE_DIR: "Claude Code",
    WORKBUDDY_DIR: "WorkBuddy",
    CUSTOM_REPO: "自定义仓库",
}

# ── 辅助 ──────────────────────────────────────────────

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> str:
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


def resolve_link(path: Path) -> str | None:
    """返回 symlink 的解析目标，不是链接则返回 None"""
    if path.is_symlink():
        try:
            return str(path.resolve())
        except OSError:
            return None
    return None


def get_skill_type(path: Path) -> str:
    """判断 skill 的存在形式: symlink / directory / git_repo / broken"""
    if path.is_symlink():
        if not path.exists():
            return "broken"
        return "symlink"
    if path.is_dir():
        if (path / ".git").exists():
            return "git_repo"
        return "directory"
    return "unknown"


def collect_all_skills(targets: list[Path] | None = None) -> dict[str, list[tuple[Path, Path]]]:
    """
    扫描指定目录（或所有标准目录），返回 {skill_name: [(base_dir, full_path), ...]}
    """
    dirs = targets or [AGENTS_DIR, CLAUDE_DIR, WORKBUDDY_DIR, CUSTOM_REPO]
    result: dict[str, list[tuple[Path, Path]]] = {}
    for base in dirs:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.name.startswith("."):
                continue
            if not item.is_dir() and not item.is_symlink():
                continue
            if item.name not in result:
                result[item.name] = []
            result[item.name].append((base, item))
    return result


# ── 健康检查 ──────────────────────────────────────────

def cmd_health():
    print("═══ 健康检查 ═══\n")

    issues = 0

    # 1. 目录存在性
    for label, path in [(".agents", AGENTS_DIR), ("Claude Code", CLAUDE_DIR),
                         ("WorkBuddy", WORKBUDDY_DIR), ("自定义仓库", CUSTOM_REPO)]:
        if path.exists():
            ok(f"{label}: {path}")
        else:
            warn(f"{label}: 路径不存在 ({path})")
            issues += 1
    print()

    # 2. 断裂链接
    broken = []
    for label, base in [("Claude Code", CLAUDE_DIR), ("WorkBuddy", WORKBUDDY_DIR)]:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.is_symlink() and not item.exists():
                broken.append((label, item.name))
    if broken:
        warn(f"{len(broken)} 个断裂链接:")
        for label, name in broken:
            warn(f"  {label}/{name}")
            issues += 1
    else:
        ok("所有符号链接有效")

    # 3. SKILL.md 缺失
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

    # 4. 非标准存在形式（非 agents 的独立目录）
    print()
    non_std = check_non_standard_skills()
    # 5. agents 目录中的 symlink 一致性
    agents_links = check_agents_symlinks_consistency()
    if agents_links:
        print()
        for name, _, target in agents_links:
            warn(f"agents/{name} -> {target}")
            issues += 1

    # 6. 非标准存在形式
    if non_std:
            label = LOCATION_LABELS.get(base, str(base))
            warn(f"  {label}/{name} 是独立目录（应为 symlink）")
            issues += 1
    else:
        ok("所有 skill 形式符合标准")

    # 5. Git 仓库状态
    if CUSTOM_REPO.exists():
        branch = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--abbrev-ref", "HEAD"])
        dirty = run(["git", "-C", str(CUSTOM_REPO), "status", "--porcelain"])
        if dirty:
            warn(f"自定义仓库 ({branch}) 有未提交变更")
            issues += 1
        else:
            ok(f"自定义仓库 ({branch}) 干净")

    print(f"\n═══ 完成: {issues} 个问题 ═══")


# ── 检测非标准 skill ──────────────────────────────────

def check_non_standard_skills() -> list[tuple[str, Path, Path]]:
    """
    返回 [(name, base_dir, full_path), ...]
    非标准条件：在 claude/workbuddy 位置中存在且是独立目录（非 symlink）
    """
    result = []
    for base in [CLAUDE_DIR, WORKBUDDY_DIR]:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_symlink():
                continue
            if item.is_dir():
                result.append((item.name, base, item))
    return result


def check_agents_symlinks_consistency() -> list[tuple[str, Path, Path]]:
    """
    检查 agents 目录中的 symlink 是否都指向有效来源。
    返回有问题的条目: [(name, agents_path, target)]
    """
    result = []
    if not AGENTS_DIR.exists():
        return result
    for item in AGENTS_DIR.iterdir():
        if not item.is_symlink():
            continue
        if item.name.startswith("."):
            continue
        if not item.exists():
            result.append((item.name, item, Path("[BROKEN]")))
            continue
        target = item.resolve()
        # agents 中的 symlink 应指向 custom_repo 或 .agents 自身
        if CUSTOM_REPO in target.parents:
            continue
        # 有些情况可能是相对路径，链式解析
        result.append((item.name, item, target))
    return result


# ── 同步 ──────────────────────────────────────────────

def cmd_sync(target: str | None = None):
    """
    默认策略：.agents/ -> claude 的单向同步。
    agents 中的每个 skill，确保 claude 有对应的 symlink。
    """
    print("═══ 同步 skills ═══\n")

    if not AGENTS_DIR.exists():
        err(".agents/skills 目录不存在，无法作为源")
        return

    if target == "claude" or target is None:
        _sync_one_target("Claude Code", CLAUDE_DIR, AGENTS_DIR)

    print("\n同步完成")


def _sync_one_target(label: str, link_dir: Path, source_dir: Path):
    if not link_dir.exists():
        warn(f"{label} 目录不存在，跳过")
        return

    ok(f"检查 {label}...")
    synced = 0
    skipped = 0
    conflicts = 0

    for skill_item in source_dir.iterdir():
        if not skill_item.is_dir() and not skill_item.is_symlink():
            continue
        if skill_item.name.startswith("."):
            continue

        link_path = link_dir / skill_item.name
        expected_target = str(skill_item.resolve())

        if link_path.is_symlink():
            existing = str(link_path.resolve())
            if existing == expected_target:
                continue  # 已指向正确目标
            link_path.unlink()
        elif link_path.exists():
            # 同名但非链接 — 冲突！报告但不自动处理
            warn(f"  冲突: {label}/{skill_item.name} 存在但不是 symlink，跳过")
            conflicts += 1
            continue
        else:
            # 不存在，直接创建
            pass

        link_path.symlink_to(expected_target)
        synced += 1
        ok(f"  链接 {skill_item.name} -> {label}")

    if synced == 0 and conflicts == 0:
        info(f"{label} 已是最新，无需同步")
    elif conflicts > 0:
        info(f"  跳过 {conflicts} 个冲突，执行 organize 处理")


# ── 整理 ─────────────────────────────────────────────

def cmd_organize():
    """
    整理技能仓库结构：
    1. 扫描所有位置的 skills
    2. 检测 claude/workbuddy 中非链接的独立目录
    3. 如该 skill 在 agents 中也有，比较内容，询问处理方式
    4. 如只在该终端有，询问是否移入 agents
    """
    print("═══ 整理 skills ═══\n")
    print("  策略: .agents/skills/ 为主仓库，其余终端仅做符号链接\n")

    # 步骤1: 查找非标准 skill
    non_std = check_non_standard_skills()
    if not non_std:
        ok("所有 skill 形式符合标准，无需整理")
        return

    if non_std:
        warn(f"发现 {len(non_std)} 个非标准 skill（独立目录在工作台）:")
    print()

    for name, base, path in non_std:
        label = LOCATION_LABELS.get(base, str(base))
        agents_skill = AGENTS_DIR / name

        print(f"  ══ {label}/{name} ══")
        print(f"     形式: 独立目录")
        print(f"     位置: {path}")

        if agents_skill.exists() or agents_skill.is_symlink():
            # 同名 skill 在 agents 中也有 — 存在冲突
            agents_type = get_skill_type(agents_skill)
            agents_short = str(agents_skill).replace(str(Path.home()), "~")
            print(f"     agents 中同名: {agents_short} ({agents_type})")

            # 比较 SKILL.md
            local_md = path / "SKILL.md"
            agents_md = agents_skill / "SKILL.md"
            local_hash = _hash_file(local_md) if local_md.exists() else ""
            agents_hash = _hash_file(agents_md) if agents_md.exists() else ""

            if local_hash and agents_hash and local_hash != agents_hash:
                print(f"     ⚡ 内容不同! 本地hash={local_hash[:8]}  agents hash={agents_hash[:8]}")
                _resolve_conflict(name, base, path, agents_skill)
            elif local_hash == agents_hash:
                print(f"     ✓ 内容相同 (hash: {local_hash})")
                _replace_with_symlink(name, base, path, agents_skill)
            else:
                print(f"     ? 无法比较 (一方的 SKILL.md 缺失)")
                _resolve_conflict(name, base, path, agents_skill)
        else:
            # agents 中没有此 skill — 询问是否移入
            print(f"     agents 中无同名 skill")
            _handle_orphan_skill(name, base, path)

        print()


def _hash_file(path: Path) -> str:
    import hashlib
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def _replace_with_symlink(name: str, base: Path, src_path: Path, target: Path):
    """用 symlink 替换独立目录"""
    import shutil
    backup = base / f"{name}_bak"
    try:
        # 重命名原目录为备份
        if not backup.exists():
            src_path.rename(backup)
            ok(f"  → 原目录已备份为: {backup.name}")
        else:
            warn("  备份目录已存在，直接移除原目录")
            shutil.rmtree(src_path)

        # 创建 symlink
        target_resolved = str(target.resolve())
        src_path.symlink_to(target_resolved)
        ok(f"  → 已替换为 symlink: {name} -> {target_resolved}")
    except Exception as e:
        err(f"  替换失败: {e}")


def _resolve_conflict(name: str, base: Path, local_path: Path, agents_path: Path):
    """冲突时询问用户处理方式"""
    print()
    print("  请选择处理方式:")
    print(f"    1) 替换 — 用 agents 版本覆盖，创建 symlink（原目录备份为 {name}_bak）")
    print(f"    2) 保留 — 当前目录重命名（如 {name}_local），然后从 agents 创建 symlink")
    print(f"    3) 跳过 — 不做处理")
    print()

    # 由于是 CLI 模式，这里走默认策略而非交互
    # 实际操作中会触发用户决策
    warn("  默认: 跳过，请显式执行 'organize <name>' 处理单个冲突")
    info("  → 如需处理，运行: python3 manage_skills.py resolve <name>")


def _handle_orphan_skill(name: str, base: Path, path: Path):
    """处理仅存在于非 agents 位置的 orphan skill"""
    print()
    print(f"  该 skill 仅在 {LOCATION_LABELS.get(base, '')} 中存在。")
    print(f"  可选操作:")
    print(f"    1) 移入 agents — 移到 {AGENTS_DIR}/{name}/，原地创建 symlink")
    print(f"    2) 跳过 — 不做处理")
    print()
    warn("  默认: 跳过。运行 'organize --move <name>' 移入agents")


# ── 单 skill 冲突解决 ────────────────────────────────

def cmd_resolve(name: str):
    """解决特定 skill 的冲突"""
    # 寻找所有出现位置
    all_skills = collect_all_skills()
    if name not in all_skills:
        err(f"未找到 skill '{name}'")
        return

    entries = all_skills[name]
    non_agents_entries = [(b, p) for b, p in entries if b != AGENTS_DIR]
    agents_entry = [(b, p) for b, p in entries if b == AGENTS_DIR]

    if not agents_entry:
        # 仅非 agents 有 → 移入 agents
        for base, path in non_agents_entries:
            if path.is_symlink():
                continue
            if path.is_dir():
                dest = AGENTS_DIR / name
                if dest.exists():
                    err(f"agents 中已有 {name}")
                    return
                path.rename(dest)
                ok(f"已移入 agents: {dest}")
                # 原地创建 symlink
                path.symlink_to(str(dest.resolve()))
                ok(f"已创建 symlink: {path} -> {dest}")
                return
        warn(f"'{name}' 在所有非 agents 位置都是 symlink，无需处理")
        return

    agents_path = agents_entry[0][1]
    for base, local_path in non_agents_entries:
        if local_path.is_symlink():
            continue
        if not local_path.exists():
            continue

        label = LOCATION_LABELS.get(base, str(base))
        print(f"处理 {label}/{name}...")

        # 比较
        local_md = local_path / "SKILL.md"
        agents_md = agents_path / "SKILL.md"
        local_hash = _hash_file(local_md) if local_md.exists() else ""
        agents_hash = _hash_file(agents_md) if agents_md.exists() else ""

        if local_hash == agents_hash:
            _replace_with_symlink(name, base, local_path, agents_path)
            return

        # 内容不同 — 询问
        print(f"  内容不同: 本地[{local_hash}] vs agents[{agents_hash}]")
        print(f"  如何处理？")
        print(f"    1) 替换 — 用 agents 版本，创建 symlink")
        print(f"    2) 保留本地 — 重命名为 {name}_local，从 agents 创建 symlink")
        # CLI 默认走选项1，因为用户可以跑之前已经思考过
        warn("  默认选项 1 (替换)。10秒内无输入则自动执行...")

        try:
            import select
            import sys as _sys
            if select.select([_sys.stdin], [], [], 10)[0]:
                choice = _sys.stdin.readline().strip()
            else:
                choice = "1"
        except Exception:
            choice = "1"

        if choice == "1":
            _replace_with_symlink(name, base, local_path, agents_path)
        elif choice == "2":
            backup_name = f"{name}_local"
            backup_path = base / backup_name
            if backup_path.exists():
                warn(f"  {backup_path} 已存在，跳过")
                return
            local_path.rename(backup_path)
            ok(f"  原目录已重命名为: {backup_name}")
            local_path.symlink_to(str(agents_path.resolve()))
            ok(f"  已从 agents 创建 symlink: {name}")
        else:
            warn("  跳过")


# ── 创建/修复链接 ────────────────────────────────────

def cmd_link(name: str):
    """为指定 skill 创建跨终端符号链接"""
    source = None
    for src_dir in [CUSTOM_REPO, AGENTS_DIR]:
        p = src_dir / name
        if (p / "SKILL.md").exists() or p.is_dir():
            source = p
            break
    if not source:
        err(f"未找到 skill '{name}'")
        return

    for link_dir, label in [(CLAUDE_DIR, "Claude Code"), (WORKBUDDY_DIR, "WorkBuddy")]:
        link_path = link_dir / name
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            warn(f"{label} 已有同名目录 {link_path}，跳过")
            continue

        link_path.symlink_to(str(source.resolve()))
        ok(f"{label}: {link_path} -> {source.resolve()}")


# ── 版本信息 ──────────────────────────────────────────

def cmd_version():
    print("═══ 版本信息 ═══\n")

    if LOCK_FILE.exists():
        with open(LOCK_FILE) as f:
            lock = json.load(f)
        print(f"🔒 .skill-lock.json v{lock.get('version', '?')}")
        skills_locked = lock.get("skills", {})
        print(f"   记录 {len(skills_locked)} 个 skill\n")
        for name, info in sorted(skills_locked.items()):
            source = info.get("source", "?")
            updated = info.get("updatedAt", "?")[:10]
            print(f"   {name:<25} {source:<35} {updated}")
    else:
        warn("未找到 .skill-lock.json")

    print()
    if CUSTOM_REPO.exists():
        branch = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--abbrev-ref", "HEAD"])
        commit = run(["git", "-C", str(CUSTOM_REPO), "rev-parse", "--short", "HEAD"])
        msg = run(["git", "-C", str(CUSTOM_REPO), "log", "--oneline", "-1"])
        print(f"📦 自定义仓库 ({branch}):")
        print(f"   {commit} {msg}")
    else:
        warn("自定义仓库不存在")

    print()
    for label, path in [(".agents", AGENTS_DIR), ("Claude Code", CLAUDE_DIR),
                         ("WorkBuddy", WORKBUDDY_DIR)]:
        if path.exists():
            count = len([p for p in path.iterdir() if not p.name.startswith(".")])
            print(f"   {label:<15} {count} skills")


# ── 更新 ──────────────────────────────────────────────

def cmd_update():
    print("═══ 更新 skills ═══\n")

    info("检查 npx skills 更新...")
    result = run(["npx", "skills", "check"])
    print(f"   {result}")
    result = run(["npx", "skills", "update"])
    print(f"   {result}")

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

    print()
    cmd_sync(None)

    print("\n更新完成")


# ── 主入口 ────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  manage_skills.py health             # 健康检查")
        print("  manage_skills.py sync [loc]         # 同步（可选: claude）")
        print("  manage_skills.py organize           # 整理: 检测冲突 + 修复")
        print("  manage_skills.py resolve <name>     # 处理特定 skill 冲突")
        print("  manage_skills.py link <name>        # 为 skill 创建链接")
        print("  manage_skills.py version            # 版本信息")
        print("  manage_skills.py update             # 更新所有 skills")
        return

    cmd = sys.argv[1]

    if cmd == "health":
        cmd_health()
    elif cmd == "sync":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_sync(target)
    elif cmd == "organize":
        cmd_organize()
    elif cmd == "resolve":
        if len(sys.argv) < 3:
            err("请指定 skill 名称: manage_skills.py resolve <name>")
            return
        cmd_resolve(sys.argv[2])
    elif cmd == "link":
        if len(sys.argv) < 3:
            err("请指定 skill 名称: manage_skills.py link <name>")
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
