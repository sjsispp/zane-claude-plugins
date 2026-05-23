---
name: architecture-verification
description: 当用户准备定稿架构分析文档但验证未通过时拦截提醒。也在用户显式提到"架构验证"、"数据验证"时触发。
version: 1.0.0
---

# 架构分析验证守护

## 触发条件（仅以下 2 种场景）

### 场景 A: 文档定稿拦截（核心）

当检测到用户准备发布/定稿架构分析文档时，检查验证状态：

**检测信号**:
- 用户说"文档完成了"、"分析结束"、"可以发布了"
- 用户准备将 architecture-analysis.md 分享或提交
- 用户准备更新 CLAUDE.md 中的项目分析引用

**检查逻辑**:

```
1. 定位 {project}/docs/arch-analysis/analysis-meta.json
2. 读取 dual_doc 验证状态

if (analysis-meta.json 不存在) {
    拦截: "分析文档未经验证，建议先 /arch-verify round 1"
}
if (dual_doc.current_round < 3) {
    拦截: "仅完成 {N}/3 轮验证，建议 /arch-verify round next 继续"
}
if (dual_doc.rounds[2].p0_pass == false) {
    拦截: "Round 3 有 P0 断言失败，建议检查分析文档"
}
if (dual_doc.rounds[2].hop_rate < 0.9) {
    提醒: "Round 3 跳通过率 {rate}% < 90%，建议 /arch-verify round next"
}
if (dual_doc.rounds[2].fk_violations > 0) {
    提醒: "{N} 处 FK 违规，建议修正后重新验证"
}
if (dual_doc.graduation.status == "pass") {
    不触发（准出门禁已通过）
}
```

### 场景 B: 用户显式提到验证

当用户在对话中提到"架构验证"、"分析验证"、"数据验证"、"验证状态"时，输出当前验证状态摘要并建议命令。

## 不触发的场景

- 用户正在执行分析过程中（Step 1-4）
- 用户在执行验证命令 `/arch-verify`
- 用户在执行循环命令 `/arch-loop`
- 分析文档不存在

## 提醒格式

简洁一行：

```
验证提醒: 仅完成 {N}/3 轮验证，建议 /arch-verify round next 后再定稿。
```

或：

```
验证提醒: Round 3 有 {N} 处 FK 违规，建议修正分析文档后 /arch-verify round 3 重新验证。
```
