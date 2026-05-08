---
name: skills-manager
description: 管理本机所有 agent skills 的安装、扫描、版本同步和状态检查。当你需要查看、管理、同步、更新本机所有 skills 时使用此技能。支持扫描 Claude Code、WorkBuddy、.agents、自定义仓库等多个位置的 skills，识别其存在形式（符号链接/独立目录/Git 仓库），并提供统一管理操作。当用户提到"管理skill"、"查看所有skill"、"同步skill"、"更新skill"、"skill版本"、"skill目录"、"skills 清单"、"skill冲突"、"整理skill"时触发。
---

# Skills Manager

管理本机所有 agent terminal 的 skills，提供统一视图和管理能力。

## 核心策略

**`.agents/skills/` 为主仓库（canonical source）**，其他终端（Claude Code、WorkBuddy）仅做符号链接。
任何在非 agents 位置出现独立目录（非 symlink）的情况都被视为非标准，需要在整理时处理。

## 扫描范围

| 路径 | 策略 | 说明 |
|------|------|------|
| `~/.agents/skills/` | 主仓库 | npx skills 安装的主要仓库 |
| `~/.claude/skills/` | 只有符号链接 | Claude Code 使用的 skills |
| `~/.workbuddy/skills/` | 只有符号链接 | WorkBuddy 使用的 skills |
| `~/repos/dxmanooskills/` | Git 仓库 | 自定义 skills 源码 |
| `~/.agents/.skill-lock.json` | 版本锁 | 版本锁定信息 |

## 使用方法

### 1. 扫描 — 查看全景
```
skills-manager scan
```
跨所有位置扫描，生成四段式管理报表：

| 段落 | 内容 |
|------|------|
| **分布一览** | 各位置 skill 总数，按 📁目录/🔗链接 分类统计 |
| **详细清单** | 按位置展开，同一位置内按形式分组列出每个 skill |
| **交叉对照** | 矩阵视图，一眼看出同名 skill 在哪些位置存在、以何种形式存在 |
| **待处理问题** | 断裂链接、非标准形式、同名内容冲突、缺失 SKILL.md 等 |

### 2. 健康检查
```
skills-manager health
```
检查断裂链接、SKILL.md 缺失、非标准形式、Git 状态等。

### 3. 同步
```
skills-manager sync          # 同步 agents → claude 的 symlink
skills-manager sync claude   # 仅同步 Claude Code
```

### 4. 整理 — 冲突检测与修复
```
skills-manager organize
```
核心整理命令：
1. 扫描所有位置的非标准 skill（非 agents 位置的独立目录）
2. 如该 skill 在 agents 中也有 → 比较 SKILL.md hash 是否一致
3. hash 不同 → 标记为冲突，**等你决策**
4. hash 相同 → 自动替换为 symlink（原目录备份为 `name_bak`）

单独处理某个冲突：
```
skills-manager resolve <skill-name>
```
交互式处理：替换（用 agents 版本）或保留（重命名为 `name_local`，再创建 symlink）。

### 5. 版本管理
```
skills-manager version       # 查看所有版本信息
skills-manager update        # 更新 npx skills + Git pull + sync
```

### 6. 创建链接
```
skills-manager link <name>   # 为 skill 创建跨终端符号链接
```

## 示例流程

```
# 1) 查看全貌
skills-manager scan

# 2) 如果发现有非标准项:
skills-manager organize

# 3) 处理单个冲突:
skills-manager resolve find-skills

# 4) 同步新链接:
skills-manager sync

# 5) 最终确认:
skills-manager health
```

## Python 脚本

- `scripts/scan_skills.py` — 扫描和形式识别、冲突检测
- `scripts/manage_skills.py` — 同步、整理、冲突解决、版本管理

配置: `config/config.json`
