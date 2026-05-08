---
name: skills-manager
description: 管理本机所有 agent skills 的安装、扫描、版本同步和状态检查。当你需要查看、管理、同步、更新本机所有 skills 时使用此技能。支持扫描 Claude Code、WorkBuddy、.agents、自定义仓库等多个位置的 skills，识别其存在形式（符号链接/独立目录/Git 仓库），并提供统一管理操作。当用户提到"管理skill"、"查看所有skill"、"同步skill"、"更新skill"、"skill版本"、"skill目录"、"skills 清单"时触发。
---

# Skills Manager

管理本机所有 agent terminal 的 skills，提供统一视图和管理能力。

## 扫描范围

自动扫描以下 skills 存放位置：

| 路径 | 类型 | 说明 |
|------|------|------|
| `~/.agents/skills/` | 独立目录 | npx skills 安装的主要仓库 |
| `~/.claude/skills/` | 符号链接 | Claude Code 使用的 skills |
| `~/.workbuddy/skills/` | 混合 | WorkBuddy 使用的 skills |
| `~/repos/dxmanooskills/` | Git 仓库 | 自定义 skills 源码 |
| `~/.agents/.skill-lock.json` | JSON | 版本锁定信息 |

## 主要功能

### 1. 扫描 (`scan`)
- 扫描所有 skills 目录
- 识别每个 skill 的存在形式（symlink / directory / git repo）
- 显示每个 skill 的状态和元信息

### 2. 查看详情 (`list` / `info`)
- 按位置分组列出所有 skills
- 查看特定 skill 的详细信息
- 检查符号链接是否断裂

### 3. 同步 (`sync`)
- 同步 `~/.claude/skills/` 和 `~/.agents/skills/` 之间的链接
- 同步自定义 skill 到各 agent 终端
- 修复断裂的符号链接

### 4. 版本管理 (`version` / `update`)
- 检查 npx skills 的版本更新
- 查看自定义 skills 的 Git 状态
- 统一升级所有可更新的 skills

### 5. 健康检查 (`health`)
- 检查所有符号链接的有效性
- 检测缺失的 SKILL.md 文件
- 检查重复或冲突的 skills

## 使用方法

### 查看所有 skills
```
skills-manager scan
```
扫描所有位置并生成完整报表。

### 查看特定位置
```
skills-manager list claude      # 仅 Claude Code 的 skills
skills-manager list workbuddy   # 仅 WorkBuddy 的 skills
skills-manager list agents      # 仅 .agents 仓库的 skills
skills-manager list custom      # 仅自定义 skills
```

### 健康检查
```
skills-manager health
```

### 同步技能
```
skills-manager sync             # 同步所有终端的 skills
skills-manager sync claude      # 仅同步 Claude Code
```

### 版本管理
```
skills-manager version          # 查看所有版本信息
skills-manager update           # 更新所有可更新的 skills
```

## Python 脚本

管理操作由 `scripts/` 目录下的 Python 脚本执行：

- `scripts/scan_skills.py` - 扫描和目录分析
- `scripts/manage_skills.py` - 同步、链接、版本管理

首次运行会自动创建配置到 `config/config.json`。
