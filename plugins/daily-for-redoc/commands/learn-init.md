---
name: learn-init
description: "初始化个人学习笔记配置。首次使用 daily-for-redoc 前必须执行。"
allowed_tools: Bash, Read, Write, AskUserQuestion
---

# /learn-init

按 `daily-for-redoc` skill 的「初始化」流程执行：

1. 询问用户主笔记 REDoc 链接（必填）
2. 用 `hi docs:extract-id` 提取 shortcutId
3. 询问 spaceId（可选）和 userName（用于子文档命名前缀）
4. 用 `hi docs:get` 验证主笔记可访问
5. 写入 `~/.claude/daily-for-redoc/config.json`

完整步骤见 skill 文档 `skills/daily-for-redoc/SKILL.md` 的「初始化」章节。
