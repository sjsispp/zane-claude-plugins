---
name: learn-deep
description: "为当前讨论开一个子文档详细记录，挂在主笔记下，并回写链接到今日 section。"
allowed_tools: Bash, Read, AskUserQuestion
arguments:
  - name: topic
    description: "子文档主题（自由文本），用于拼接标题 YYYY-MM-DD-<主题>"
    required: false
---

# /learn-deep

按 `daily-for-redoc` skill 的「开子文档」流程执行：

1. 读 config，拿 `mainDocShortcutId` / `spaceId` / `userName`
2. 询问/确认主题（若已在 args 中提供 `topic` 则直接用）
3. 按固定结构生成子文档内容：背景 / 关键问题 / 结论 / 关键对话片段
4. 执行 `utils:generate-operate-code` 拿幂等码
5. `hi docs:create --parent-id <主笔记> --title "YYYY-MM-DD-<主题>"`
6. 重新 `docs:get` 主笔记拿新 hash，回写「深入阅读」链接到今日 section
7. 返回主笔记 + 子文档两个链接

完整模板、命名规则与 hash 流转细节见 skill 文档 `skills/daily-for-redoc/SKILL.md` 的「开子文档」章节。
