---
name: arch-template
description: 获取架构分析文档模板，支持完整模板或各层专项模板
allowed_tools: Read, Write
arguments:
  - name: type
    description: "模板类型：full(完整模板), L0-L6(各层专项), mermaid(图表模板), tables(表格模板)"
    required: false
    default: full
  - name: output
    description: "输出路径，不指定则直接输出到对话"
    required: false
---

# 架构分析模板获取命令

根据 `$ARGUMENTS.type` 参数提供对应的模板。

## 模板类型说明

| 类型 | 说明 |
|------|------|
| `full` | 完整的七层递进分析文档模板 |
| `L0` | L0：服务全景专项模板（入口/依赖/流量） |
| `L1` | L1：项目概览专项模板 |
| `L2` | L2：业务全景专项模板 |
| `L3` | L3：核心链路专项模板（核心业务/链路识别） |
| `L4` | L4：技术流程专项模板 |
| `L5` | L5：数据模型专项模板 |
| `L6` | L6：配置与扩展专项模板 |
| `mermaid` | Mermaid 图表模板库 |
| `tables` | 表格模板库 |

## 执行流程

1. 读取技能引用中的模板文件：`${CLAUDE_PLUGIN_ROOT}/skills/architecture-analysis/references/`
2. 根据 type 参数选择对应模板内容
3. 如果指定了 output 路径，写入文件；否则直接输出到对话

## 输出要求

- 模板内容使用 markdown 代码块包裹，便于用户复制
- 提供简要的使用说明
- 说明如何配合 `/arch-analyze` 命令使用
