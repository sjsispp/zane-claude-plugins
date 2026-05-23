---
name: arch-analyze
description: "启动项目架构分析（双文档交替驱动验证闭环）。支持: /arch-analyze [场景描述] [depth=quick|standard|deep]"
allowed_tools: Glob, Grep, Read, LS, Task, Write, Edit, TodoWrite, AskUserQuestion, mcp__plugin_xhs-tools_xhs-tools__batch_query_upstream, mcp__plugin_xhs-tools_xhs-tools__batch_query_downstream, mcp__plugin_xhs-tools_xhs-tools__query_rpc_topology, mcp__plugin_xhs-tools_xhs-tools__query_mq_by_key, mcp__plugin_xhs-tools_xhs-tools__list_jobs, mcp__plugin_xhs-tools_xhs-tools__list_all_jobs, mcp__plugin_xhs-tools_xhs-tools__execute_dms_sql_query, mcp__plugin_xhs-tools_xhs-tools__get_cached_table_schema, mcp__plugin_xhs-tools_xhs-tools__get_table_structure, mcp__plugin_xhs-tools_xhs-tools__search_table_column, mcp__plugin_xhs-tools_xhs-tools__get_apollo_config_value, mcp__plugin_xhs-tools_xhs-tools__search_apollo_config, mcp__plugin_xhs-tools_xhs-tools__query_xray_logs, mcp__plugin_xhs-tools_xhs-tools__locate_table, mcp__plugin_xhs-tools_xhs-tools__search_xray_field_values, mcp__plugin_xhs-tools_xhs-tools__build_trace_query
arguments:
  - name: scenario
    description: "分析场景描述（自由文本）。如 '结算链路', '退款流程', '订单状态推进'。提供后将聚焦该场景进行数据采集和验证"
    required: false
  - name: depth
    description: "分析深度：quick(快速概览), standard(标准分析), deep(深度分析)"
    required: false
    default: standard
  - name: output
    description: "输出路径，默认为项目 docs/ 目录"
    required: false
---

# 项目架构分析命令

你是一名资深软件架构师，擅长快速理解陌生项目并产出清晰的架构分析文档。

## 参数解析

`$ARGUMENTS` = "{{$ARGUMENTS}}"

**智能参数解析**：用户输入的非 `key=value` 格式文本自动识别为 `scenario`（分析场景）。

```
/arch-analyze                        → 全项目分析，数据驱动验证闭环
/arch-analyze 结算链路                → 聚焦"结算链路"场景
/arch-analyze 退款流程 depth=deep     → 聚焦"退款流程"，deep 深度
```

当提供 `scenario` 时：
1. Step 1 数据采集聚焦于该场景相关的 RPC/MQ/表/配置
2. Step 2 跳过交互确认，直接以该场景为核心链路
3. Step 3 针对该场景采集 DMS + XRay 数据
4. Step 4-5 围绕该场景进行分析和验证

## 核心理念

**没有逐跳数据证据的分析结论不可信。** 所有分析结论必须经过 3 轮双文档交替驱动验证闭环。

> 直接 `/arch-analyze` 或 `/arch-analyze XXX场景` 即启动完整数据驱动验证闭环，无需额外参数。

## 分析深度说明

根据 `$ARGUMENTS.depth` 参数选择分析深度：

| 深度 | 覆盖层级 | 产出内容 | 适用场景 |
|------|---------|---------|---------|
| `quick` | L0-L1 | 服务全景 + 项目概览 | 快速了解（5-10分钟） |
| `standard` | L0-L4 | 加上业务全景 + 核心链路 + 技术流程 | 日常分析（20-30分钟） |
| `deep` | L0-L6 | 完整分析（含全量 ER 图） | 深度研究（45-60分钟） |

## 七层递进框架

| 层级 | 名称 | 核心内容 | 版本 |
|------|------|---------|------|
| **L0** | 服务全景 | 入口/依赖/DB 统计 + 流量概览 | - |
| L1 | 项目概览 | 系统定位、业务价值 | - |
| L2 | 业务全景 | 场景分类、触发来源 | - |
| **L3** | 核心链路 | 核心业务识别 + 链路深度分析 | - |
| L4 | 技术流程 | 时序图、状态机 | - |
| **L5** | 数据模型 | 全量 ER 图 + 表结构详情 | - |
| L6 | 配置扩展 | 配置项、策略规则 | - |

---

## 执行流程

### Step 1: 环境检测 + 全量数据采集

**1.1 环境检测**：
1. 确认当前工作目录是否为有效项目
2. 检测项目技术栈（语言、框架、构建工具）
3. 从 pom.xml 或 build.gradle 提取项目名称（artifactId）
4. 确定输出目录（默认 `docs/architecture-analysis.md`）
5. 创建数据持久化目录 `docs/arch-analysis/collected-data/`
6. 初始化 `docs/arch-analysis/analysis-meta.json`

**1.2 全量数据采集**（并发执行 3 个子 Agent）：

| 子 Agent | 采集内容 | 工具 | 输出文件 |
|---------|---------|------|---------|
| Agent 1 | RPC 上下游拓扑 + 方法级流量 | batch_query_upstream + batch_query_downstream + query_rpc_topology | topology.json |
| Agent 2 | MQ 流量 + Job 信息 | query_mq_by_key + list_jobs | mq-traffic.json, jobs.json |
| Agent 3 | 表结构 + Apollo 配置 | get_cached_table_schema + search_apollo_config + get_apollo_config_value | table-schemas.json, apollo-configs.json |

**同时执行代码扫描**（3 个 Agent）：

**Agent 4 - RPC/MQ 依赖分析**（代码扫描 + 数据合并）：
```
1. 代码扫描：ClientBuilder.create、@Resource + Iface、Events.publish
2. 合并 Agent 1 的运行时数据
3. 如有 deps.json 存在则直接复用
输出：上游调用统计表、下游依赖统计表
```

**Agent 5 - 服务入口扫描**：
```
扫描对象：RPC Server、MQ Consumer、HTTP Controller、JOB
输出：服务入口统计表（类型、数量、TOP3 接口）
```

**Agent 6 - 数据实体扫描**：
```
扫描对象：@TableName / @Table
输出：DB 表统计
```

> 详细采集策略参考 `references/data-collection-guide.md`。

### Step 2: 核心链路识别

基于 Step 1 实际采集的流量数据，识别核心业务和链路。

#### 2.1 项目概览 + 业务场景识别（L1-L2）

**Agent 1 - 项目概览**：读取 README.md、pom.xml 等识别系统定位

**Agent 2 - 业务场景识别**（4 个子步骤）：
- **Step 2.1 识别触发源**：基于 L0 扫描结果
- **Step 2.2 分类业务场景**：搜索 bizScene/bizIdentity 字段 + Apollo Map 配置
- **Step 2.3 识别配置驱动路径**（条件执行）：场景识别信号检查表命中 >= 2 项时执行
- **Step 2.4 交互确认业务场景**

#### 2.2 核心业务/链路识别（L3）

> 加载 `${CLAUDE_PLUGIN_ROOT}/skills/architecture-analysis/references/traffic-guide.md` 获取流量分析和核心链路识别方法论。

**评估维度**：
| 维度 | 权重 | 数据来源 |
|------|------|---------|
| 流量量级 | 40% | Step 1 topology.json 实际流量 |
| 业务重要性 | 30% | 主流程 > 辅助流程 |
| 操作类型 | 20% | 写操作 > 读操作 |
| 复杂度 | 10% | 链路数量、MQ 消息量、Job 频率 |

使用 `AskUserQuestion` 让用户确认核心业务和链路。

### Step 3: 线上数据采集

> 对每个已确认的核心业务场景采集线上数据。

**采集要求**：
- DMS 查询 >= 10 条记录/场景（覆盖正常/边缘/异常）
- XRay 日志查询（成功 trace + 失败 trace）
- 持久化到 `collected-data/scenarios/{scenario}-data.json`

详细采集规则参考 `references/data-collection-guide.md` Step 3 章节。

### Step 4: 组合分析（L0-L6）

执行七层分析，**增强为数据验证版**：

#### 场景差异分析（条件执行）

> 仅在 Step 2 识别到多场景系统且用户确认后执行。

1. 构建事件×场景处理矩阵
2. 构建能力使用矩阵
3. 核心公式差异分析

**配置数据获取优先级**：
| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | Step 1 采集的 apollo-configs.json | 实时数据 |
| 2 | Apollo 快照 | `{project}/docs/config/apollo-config-*.json` |
| 3 | MCP 工具实时获取 | `get_apollo_config_value(key, env)` |
| 4 | 代码逻辑推断 | 从默认值、注释、测试用例推断 |

#### 各层分析增强

| 层级 | 数据增强 | 验证方式 |
|------|---------|---------|
| L0 | 流量来自 topology.json 实际采集 | V-TOPO + V-ENTRY |
| L1-L2 | 配置来自 apollo-configs.json | V-CFG |
| L3 | 链路数据来自 XRay trace | V-FLOW + V-REL |
| L4 | 时序图基于 XRay trace 生成 | V-FLOW + V-STS |
| L5 | ER 图基于实际表数据验证 | V-DATA + V-REL |
| L6 | 配置值来自 Apollo 实际值 | V-CFG |

**分析模式对比**：

| 分析项 | standard | deep |
|--------|:-------:|:----:|
| 场景级配置识别 | L2 完成 | L2 完成 |
| 事件×场景矩阵 | L2 完成 | L2 完成 |
| **L4.4 错误码速查** | **TOP10 高频** | **全量+排查路径** |
| **L5.6 DMS 查询模板** | -- | **核心表全量** |
| **L5.7 数据库抽样验证** | **仅空表检测** | **完整抽样** |
| **L5.8 字段类型检查** | -- | **全量类型比对** |
| **附录 D: XRay 模板** | **3 种基础** | **基础+链路定制** |
| **附录 E: 决策树** | -- | **文本树+排查手册** |
| **附录 F: 验证报告** | **摘要** | **完整报告** |

### Step 5: 双文档交替驱动验证（3轮强制）

执行分析文档 ↔ 验证文档交替驱动验证循环：

#### Round 1 — 初始验证

1. 读取 Step 4 分析文档
2. 将分析文档保存为 `docs/arch-analysis/chains/{chain}-analysis.md`
3. 对每条链路的每一跳:
   a. 查表结构 (`get_cached_table_schema`) 确定 FK 字段
   b. 按 FK 优先级生成 FK-first SQL（禁止泛化主键）
   c. 执行 DMS 查询验证
   d. 记录: SQL + 结果 + FK类型 + PASS/FAIL
4. 执行跨步金额一致性 + 时序校验
5. 输出 `verification/round-1-verification.md`（不可修改）
6. 汇总: 跳通过率、FK 合规率、FAIL 项列表

#### 分析文档修正（Round 1 → Round 2）

1. 读取 Round 1 FAIL 项
2. 修正 `chains/{chain}-analysis.md` 中错误的链路/FK/表关系
3. 标注修正内容（diff 形式）

#### Round 2 — 修正后验证

1. 基于修正后的分析文档重新生成全部 SQL
2. 关注 Round 1 FAIL 项是否修复
3. 同时验证未变化的跳（防止回归）
4. 输出 `verification/round-2-verification.md`

#### 分析文档二次修正（Round 2 → Round 3）

同上。

#### Round 3 — 最终全量验证

1. 完整重新验证所有跳（不跳过）
2. 输出 `verification/round-3-verification.md`
3. 执行准出门禁检查（4 条件）

#### 准出门禁

```
rounds == 3                    AND
P0 assertions ALL PASS         AND
hop_pass_rate >= 90%           AND
fk_violation_count == 0
```

通过 → 生成 `graduation-report.md`，文档定稿。
未通过 → 标记需人工审查。

> FK 优先级层级和准出门禁详细定义参考 `references/verification-guide.md`。
> 每轮验证文档模板参考 `references/verification-doc-template.md`。

### Step 6: 文档输出 + 持续循环

1. 读取 `complete-template.md` 获取文档结构
2. 写入 `{project}/docs/architecture-analysis.md`
3. 写入验证报告（附录 F）
4. 更新 `analysis-meta.json`
5. 将项目关键信息写入项目级 CLAUDE.md
6. 提示用户可通过 `/arch-verify gate` 检查准出门禁，或 `/arch-loop auto` 继续迭代优化

---

## 输出格式要求

- 使用 Mermaid 绘制所有架构图、流程图、时序图
- 使用表格总结关键信息，避免冗余描述
- 每层提供"阅读提示"说明本层价值
- 代码引用使用 `file_path:line_number` 格式
- 核心链路分析控制在半页内，突出关键信息

## 注意事项

- 先理解业务含义，再关注技术实现
- 图表建立直觉，表格补充细节
- 每个章节可独立阅读
- 遵循项目现有的语言风格（中文/英文）
- 核心业务和链路必须交互确认（除非 scenario 已指定），避免遗漏用户关注的内容
- **优先使用 MCP 工具采集运行时数据**，仅在工具不可用时降级到代码扫描
- **每个分析结论必须标注数据来源**（文件:行号 或 MCP 查询结果）

开始分析当前项目。
