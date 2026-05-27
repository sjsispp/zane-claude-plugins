---
name: daily-for-redoc
description: 个人学习/工作笔记 skill。把与 AI 对话的学习或工作内容总结后按今日日期追加到个人 REDoc 主笔记文件，并在内容深度足够时主动询问是否开子文档详细记录。当用户说「帮我写在我的个人笔记中」「记到我的笔记里」「写到学习日报」「记一下今天学的」或调用 `/learn-init`、`/learn-log`、`/learn-deep` 时触发。
---

# daily-for-redoc

把和 AI 对话的学习/工作产出，结构化追加到个人 REDoc 主笔记（按日期分 section），并按需开子文档详细记录。

## 配置文件

位置固定：`~/.claude/daily-for-redoc/config.json`

```json
{
  "mainDocShortcutId": "<主笔记 shortcutId>",
  "spaceId": null,
  "userName": "<用户名前缀，用于子文档标题>"
}
```

读取前先 `test -f` 判断；不存在则提示用户先运行 `/learn-init`。

## 触发路由

| 用户意图 | 走哪个流程 |
|---|---|
| 首次使用 / 重新配置 | [初始化](#初始化) |
| 「帮我写在我的个人笔记中」「记到我的笔记里」`/learn-log` | [追加今日笔记](#追加今日笔记) |
| AI 判断对话值得留档 → 询问 → 同意 / `/learn-deep <主题>` | [开子文档](#开子文档) |

---

## 初始化

1. 询问主笔记 REDoc 链接（必填）：
   ```bash
   hi docs:extract-id --url "<用户给的链接>"
   ```
   拿到 `shortcutId`。
2. 询问 `spaceId`（可选，跳过则置 null）。
3. 询问 `userName`（用于子文档命名前缀）。
4. 验证主笔记可访问：
   ```bash
   hi docs:get --shortcut-id "<shortcutId>"
   ```
   成功则写入配置；失败提示用户检查权限。
5. `mkdir -p ~/.claude/daily-for-redoc` 后写入 `config.json`。

---

## 追加今日笔记

### 第 1 步：总结对话

按下表挑选写入哪几栏。**两栏都为空时拒绝写入**，提示用户对话太短。

| 对话特征 | 渲染 |
|---|---|
| 全程问答/解释概念 | 只写「学到了什么」 |
| 包含任务执行、代码改动、决策 | 加上「做了什么」 |

要点写作规范（严格遵守，不达标必须砍）：

**硬性约束**
- **每条 ≤ 20 字**。超出 → 拆条；拆不动 → 删
- **每个主题（学到/做了）1-2 条封顶**。多余的砍到最关键的留下
- 写不出 ≤ 20 字的版本 → 那条本来就不重要，不要写
- 给**名词与结论**，不给动词流水账与论证过程
- 禁用回顾性主语：「我们」「你」「讨论了」「学到了」「了解到」
- 行动条目格式：`<动作><对象>（<产物链接>）`，无产物链接通常说明这事没做完，不写

**正反例**

学到了什么：
- ❌ 我们讨论了 hi-cli 的 docs:get 命令，它会返回 mdPath、sourcemapPath 和 hash 三个字段，其中 hash 是后续 edit 操作必传的
- ✅ docs:get 返回的 hash 是 edit 必传参数
- ❌ 了解到 REDoc 的 markdown 渲染对 `<` `>` `{` `}` 等特殊字符需要做 HTML 实体转义否则会出现解析错误
- ✅ REDoc 普通文本中 `<>{}` 必须转 HTML 实体

做了什么：
- ❌ 创建了一个新的 Claude Code 插件叫 daily-for-redoc，并把它推送到了 github 仓库
- ✅ 新建 daily-for-redoc 插件并推送（[commit](url)）

### 第 2 步：读主笔记

```bash
hi docs:get --shortcut-id "<mainDocShortcutId>"
```

返回 `{ mdPath, sourcemapPath, hash }`。读取 `mdPath` 全文，查找今日日期 section：`## YYYY-MM-DD`（用真实日期，例如 `## 2026-05-27`）。

### 第 3 步：写入（两种情况）

**情况 A：今日 section 已存在**

在对应栏目末尾追加。`--target` 选「该 section 内某一行 + 紧接其后的下一行」组合作为锚，确保唯一。

```bash
hi docs:edit \
  --shortcut-id "<mainDocShortcutId>" \
  --hash "<上一步的 hash>" \
  --target "<某条原有要点>
<下一行内容，确保此 target 在全文唯一>" \
  --replace "<原 target 内容>
- <新要点>"
```

**情况 B：今日 section 不存在**

把新 section 插在文档标题下方（保持「最新在上」）。`--target` 锚定文档第一行标题。

```bash
hi docs:edit \
  --shortcut-id "<mainDocShortcutId>" \
  --hash "<上一步的 hash>" \
  --target "# <主笔记原标题>" \
  --replace "# <主笔记原标题>

## YYYY-MM-DD

### 学到了什么
- <要点 1>
- <要点 2>

### 做了什么
- <行动 1>"
```

`### 做了什么` 没有内容时整段省略。

### 第 4 步：判断是否需要开子文档

满足以下任一信号时，**主动询问用户**「要不要为「<主题>」开个子文档详细记录？」：
- 对话有完整的「问题 → 分析 → 结论」链条
- 跨多轮迭代、有反复修正
- 含较长代码示例、技术决策依据

用户同意 → 进入「开子文档」流程。

### 第 5 步：返回主笔记链接

`https://docs.xiaohongshu.com/doc/<mainDocShortcutId>`

---

## 开子文档

### 第 1 步：生成子文档内容

固定结构：

```markdown
## 背景
<为什么会讨论这个>

## 关键问题
<核心问题清单>

## 结论
<最终结论或方案>

## 关键对话片段
<必要的代码/原话引用>
```

### 第 2 步：创建子文档

挂在主笔记下，标题格式 `YYYY-MM-DD-<主题>`：

```bash
# 生成幂等操作码
OPERATE_CODE=$(bunx @xhs/hi-cli@latest utils:generate-operate-code)

hi docs:create \
  --title "YYYY-MM-DD-<主题>" \
  --content "<上一步生成的 Markdown 正文>" \
  --parent-id "<mainDocShortcutId>" \
  --operate-code "$OPERATE_CODE"
```

如配置了 `spaceId`，加上 `--space-id <spaceId>`。返回 `{ shortcutId, url }`。

### 第 3 步：回写链接到主笔记

在今日 section 内追加「### 深入阅读」条目。先 `docs:get` 拿最新 hash（前面写过主笔记，hash 已变）：

```bash
hi docs:get --shortcut-id "<mainDocShortcutId>"
```

再 edit。target 选今日 section 标题：

```bash
hi docs:edit \
  --shortcut-id "<mainDocShortcutId>" \
  --hash "<新 hash>" \
  --target "## YYYY-MM-DD" \
  --replace "## YYYY-MM-DD

### 深入阅读
- [<子文档标题>](<子文档 url>)"
```

若今日 section 已有「### 深入阅读」小节，改为在该小节末尾追加（参考「追加今日笔记 → 情况 A」）。

### 第 4 步：告知用户

返回主笔记 + 子文档两个链接。

---

## 关键约束

- **每次 `docs:edit` 前必须 `docs:get` 拿最新 hash**。多步操作之间 hash 会失效。
- **`--target` 必须在全文唯一**，否则 edit 会失败。不唯一时拓宽上下文（多带一行）。
- **创建子文档前必须执行 `utils:generate-operate-code`**（每次新建都要新的 operateCode，保证幂等）。
- **写入前不主动询问授权**：「帮我写在我的个人笔记中」本身就是授权，但要在响应里告知「已写入 <link>」让用户验证。
- **Markdown 转义**：普通文本中的 `<` `>` `{` `}` 要转义为 HTML 实体；表格内 `|` 转 `&#124;`；代码块内不转义。详见 `hi docs:markdown-syntax`。

## 错误处理

| 错误 | 处理 |
|---|---|
| hash 冲突（提示版本过期） | 重新 `docs:get` 取 hash，重试一次 |
| `--target` not found / 不唯一 | 拓宽 target 上下文重试；3 次失败转人工 |
| config 不存在 | 引导用户运行 `/learn-init` |
| `docs:get` 权限失败 | 提示用户检查 shortcutId 是否正确、是否有权限 |
