---
name: learn-log
description: "把当前对话总结后追加到今日个人笔记。等同于用户说「帮我写在我的个人笔记中」。"
allowed_tools: Bash, Read, AskUserQuestion
---

# /learn-log

按 `daily-for-redoc` skill 的「追加今日笔记」流程执行：

1. 读 `~/.claude/daily-for-redoc/config.json`（缺失则引导 `/learn-init`）
2. 总结当前对话为「学到了什么」+（可选）「做了什么」两栏
3. `hi docs:get` 拿主笔记 mdPath + hash
4. 判断今日日期 section 是否存在：
   - 存在 → `hi docs:edit --target ... --replace ...` 在对应栏目末尾追加
   - 不存在 → 在文档标题下方插入新 section
5. 完成后判断是否需要开子文档，需要则询问用户
6. 返回主笔记链接

完整规则、模板、target 选取与 hash 处理见 skill 文档 `skills/daily-for-redoc/SKILL.md` 的「追加今日笔记」章节。
