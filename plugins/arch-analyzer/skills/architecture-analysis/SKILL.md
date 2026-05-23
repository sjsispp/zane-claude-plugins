---
name: architecture-analysis
description: 当用户需要分析项目架构、理解陌生系统、梳理业务流程、或生成架构文档时使用此技能。提供七层递进分析框架（含服务全景与核心链路识别）和业务场景梳理方法论。
version: 4.0.0
---

# 项目架构分析方法论

## 概述

本技能提供系统化的项目架构分析方法，帮助快速理解陌生项目。采用"业务优先、场景驱动、流程清晰、配置落地"的分析理念。

**核心思想**：理解一个系统的关键是理解它的**业务场景**和**核心链路**。同一套代码在不同配置下会产生不同的业务行为，因此分析必须将"代码逻辑"与"配置规则"结合起来。

## 七层递进分析框架

```
L0: 服务全景     → 入口/依赖/DB 统计 + 流量概览（新增）
L1: 项目概览     → 这是什么系统？系统定位、业务价值
L2: 业务全景     → 场景矩阵（事件×场景×行为）、触发来源、业务身份体系
L3: 核心链路     → 核心业务/链路识别 + 深度分析（新增）
L4: 技术流程     → 技术如何实现？时序图、状态机
L5: 数据模型     → 数据如何组织？全量 ER 图、表结构
L6: 配置与扩展   → 行为如何控制？配置项、策略规则
```

### 框架对比

| 层级 | 名称 | 核心问题 | 输出物 | 版本 |
|------|------|---------|--------|------|
| **L0** | 服务全景 | 系统入口和依赖是什么？ | 入口统计表、依赖统计表、流量概览 | - |
| L1 | 项目概览 | 这是什么系统？ | 系统定位图、能力矩阵 | - |
| L2 | 业务全景 | 支持哪些业务？ | 业务场景树、触发汇总表 | - |
| **L3** | 核心链路 | 核心业务如何流转？ | 核心业务识别、链路深度分析 | - |
| L4 | 技术流程 | 技术如何实现？ | 时序图、状态转换图 | - |
| **L5** | 数据模型 | 数据如何组织？ | **全量 ER 图**、表结构详情 | - |
| L6 | 配置扩展 | 行为如何控制？ | 配置清单、策略规则表 | - |

### 阅读路径建议

| 目的 | 推荐层级 | 分析深度 |
|------|---------|---------|
| 快速了解 | L0-L1 | quick |
| 业务理解 | L0-L4 | standard |
| 深度研究 | L0-L6 | deep |
| 排查问题 | L3-L4 + L6 | 按需 |

---

## L0 服务全景

### 扫描内容

| 类别 | 扫描项 | 识别模式 |
|------|--------|---------|
| **服务入口** | RPC Server | `implements XxxService.Iface` |
| | MQ Consumer | `@XhsConsumer` / `@RocketMQMessageListener` |
| | HTTP Controller | `@RestController` + `@RequestMapping` |
| | 定时任务 | `@Scheduled` / `@XxlJob` |
| **下游依赖** | RPC Client | `ClientBuilder.create` / `@Resource + Iface` |
| | MQ Producer | `Events.publish` / `sendAsync` |
| | DB Entity | `@TableName` / `@Table` |

详细识别模式参考 `references/code-patterns.md`。

### 流量数据获取

1. **检测数据目录**：`{project}/docs/rpc-analysis/`
2. **加载依赖文件**：`{service}-deps.json`
3. **解析流量数据**：
   - `upstream[]` - 上游调用方（谁调用本服务）
     - `upstream[].targetMethod` - 被调用的方法
     - `upstream[].callerApp` - 调用方应用
     - `upstream[].callerMethod` - 调用方方法
     - `upstream[].calls` - 14天调用量
   - `rpc[]` - 下游依赖（本服务调用谁）
     - `rpc[].calls` - 14天调用量
     - `rpc[].avgLatency` - 平均延迟
   - `mq[].calls` - MQ 消息量
4. **降级策略**：无流量数据时，基于代码静态分析评估重要性

### 输出格式

```markdown
## L0 服务全景

### 服务入口统计
| 类型 | 数量 | TOP3 接口 | 14天流量 |
|-----|------|----------|---------|
| RPC | 12 | settlement, query, batch | 2.46亿 |
| MQ | 3 | settle_topic | 6094万 |
| HTTP | 5 | /api/health | - |
| JOB | 2 | syncJob | - |

### 上游调用统计（谁调用本服务）
| 入口方法 | 调用方 | 调用方方法 | 14天流量 | 平均耗时 |
|---------|-------|-----------|---------|---------|
| applySingleSettle | luna-service-thirdparty | changeAmount | 1.15亿 | 206ms |
| applyReceiveSettle | redsettleacceptance | executeCommand | 1万 | 9.66ms |

### 下游依赖统计（本服务调用谁）
| 类型 | 数量 | TOP3 依赖 |
|-----|------|----------|
| RPC | 15 | redaccountcore, redpaycore |
| MQ | 1 | settle_finish_topic |
| DB | 8 | t_settlement_record |
```

---

## L3 核心链路识别

### 两层结构

核心业务和核心链路是分层的：

```
核心业务（Business）
├── 结算业务
│   ├── 正向结算链路（Flow）
│   ├── 逆向结算链路
│   └── 批量结算链路
└── 分账业务
    ├── 申请分账链路
    └── 取消分账链路
```

### 识别流程

1. **识别核心业务**：聚合相关接口，计算业务级流量
2. **用户确认**：展示候选业务，使用 `AskUserQuestion` 确认
3. **识别核心链路**：在确认的业务下识别具体链路
4. **用户确认**：展示候选链路，确认分析范围
5. **深度分析**：对确认的链路进行详细分析

### 评估维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 流量量级 | 40% | 从 rpc-analysis 数据获取 |
| 操作类型 | 30% | 写操作 > 读操作 |
| 入口类型 | 20% | RPC/MQ > HTTP > JOB |
| 业务重要性 | 10% | 主流程 > 辅助 |

详细识别方法参考 `references/traffic-guide.md`。

### 深度分析输出

每条核心链路的分析内容：

| 分析项 | 格式 | 要求 |
|--------|------|------|
| 业务流程图 | Mermaid flowchart | 5-8 个节点 |
| 数据流转表 | 表格 | 涉及表 + 操作类型 |
| 状态机 | Mermaid stateDiagram | 仅有状态变化时 |
| 核心代码 | 表格 | 类:方法:行号 |

---

## L5 数据模型增强

### 全量 ER 图

- 扫描所有 `@TableName` / `@Table` 注解
- 结合 DMS 工具获取表结构（如可用）
- 生成服务级完整 ER 图

### 表结构详情

对核心表提供：
- 字段说明（业务含义）
- 索引信息
- 关联关系

---

## 业务场景梳理四步法

### 第一步：识别触发源

系统的入口在哪里？

| 触发类型 | 识别方法 | 关键信息 |
|---------|---------|---------|
| MQ 消息 | Consumer 类、@MQConsumer | Topic、Tag、消息体 |
| RPC 调用 | Server 类、Thrift IDL | 服务名、方法名 |
| 定时任务 | Job 类、@Scheduled | Cron、执行逻辑 |
| HTTP 接口 | Controller 类 | 路径、参数 |

### 第二步：分类业务场景

系统支持哪些业务？

- 按业务方向：正向 vs 逆向（如：支付 vs 退款）
- 按业务主体：B2C vs C2C vs B2B
- 按业务类型：标准流程 vs 特殊流程
- 按地域/渠道：国内 vs 跨境

### 第二步半：识别配置驱动的业务路径

> **触发条件**：使用"场景识别信号检查表"（见 `references/table-templates.md`）检查 4 项信号，**命中 2 项及以上**则执行本步骤。未命中或仅命中 1 项则跳过，直接进入第三步。

**识别步骤**：

1. **识别分发器模式**：
   - `Map<String, Handler>` 策略分发
   - `switch(bizScene)` / `if-else` 场景分支
   - `@ApolloJsonValue` + Map 类型配置驱动

2. **提取业务身份体系**：
   - Apollo 配置命名模式：`{prefix}.{bizIdentity}.{bizScene}` 或 `{prefix}.{bizScene}.{bizEvent}`
   - 枚举类扫描：`rg "enum.*Scene|enum.*Identity|enum.*Event" src/main`
   - 三级身份：bizIdentity（一级） → bizScene（二级） → bizEvent（三级）

3. **构建事件×场景矩阵**：
   - 行 = 事件（如 ORDER_PAID、ORDER_FINISHED、ORDER_RETURN）
   - 列 = 场景（如 DE、EE、C2C）
   - 单元格 = 处理行为（计费指令数、能力组合）
   - 参考 `references/table-templates.md` 中的"事件×场景处理矩阵"模板

### 第三步：分析场景差异

同一事件在不同场景下有何不同？

**分析方式**：采用**横切对比**（按维度/能力分章节对比各场景），而非纵切（按场景分章节各自描述）。

| 分析维度 | 关注点 |
|---------|--------|
| 触发时机 | 某事件是否触发处理？何时触发？ |
| 处理能力 | 触发哪些能力/组件？ |
| 配置差异 | 各场景的 Apollo 配置有何不同？ |
| 公式差异 | 金额计算公式有何不同？ |
| 数据差异 | 需要哪些额外数据？ |
| 下游调用 | 调用哪些下游系统？ |

**产出格式**（参考 `references/table-templates.md`）：
1. 事件×场景处理矩阵 — L2 核心产出
2. 能力使用矩阵 — L2 条件产出（多场景系统）
3. 核心公式差异对比表 — L2 简化版 / L6 全量版

### 第四步：映射配置规则

配置如何决定业务行为？

```
真实业务行为 = 通用代码逻辑 × 配置规则
```

**具体步骤**：
1. **定位配置加载代码**：搜索 `@ApolloJsonValue`、`@Value` 注解
2. **提取配置 key 模式**：识别 `{prefix}.{bizScene}.{capability}` 等命名模式
3. **读取配置值**：优先使用 Apollo 快照（`{project}/docs/config/apollo-config-*.json`），备选用 MCP 工具实时获取
4. **对比差异**：提取各场景配置，横切对比差异点
5. **关联代码行为**：将配置差异映射到代码执行路径差异

| 配置类型 | 作用 | 识别方法 | 示例 |
|---------|------|---------|------|
| 业务身份匹配 | 决定适用哪套规则 | `rg "bizIdentity\|bizScene\|bizEvent"` | bizIdentity:bizScene:bizEvent |
| 能力开关 | 决定启用哪些处理能力 | `rg "settleCapability\|capability"` | POSITIVE_RECEIVE, ROYALTY |
| 金额公式 | 决定金额如何计算 | `rg "MVEL\|formula\|expression"` | `-fyiPromotionFee` |
| 策略参数 | 决定参数取值方式 | `rg "FIXED\|FEE_ITEM"` | ratingUserId = MVEL: sellerId |

---

## 运维排查能力生成

> 自动为项目生成可直接使用的排查模板。所有内容均为**条件生成**，不满足检测条件时自动跳过。

### 生成内容总览

| 生成内容 | 检测条件 | 所属层级 | 深度要求 | 说明 |
|---------|---------|---------|---------|------|
| 错误码速查 | 错误码定义 >= 3 个 | L4.4 | standard+ | 映射错误码到排查路径 |
| DMS 查询模板 | 存在 @TableName/@Table | L5.6 | deep | 按表生成可用 SQL |
| XRay 查询模板 | L0 识别到服务入口 | 附录 D | standard+ | 按服务和链路生成查询 |
| 故障诊断决策树 | L4 异常策略 >= 3 种 | 附录 E | deep | 文本决策树 + 排查手册 |

### 错误码扫描模式

```bash
# 1. 枚举错误码（最常见）
rg -t java "enum.*(Error|Result|Biz)Code"

# 2. 常量错误码
rg -t java "(ERROR_CODE|ERR_|FAIL_).*="

# 3. 自定义异常类
rg -t java "class.*extends.*(Exception)"

# 4. 响应码引用
rg -t java "ResultCode\.|ResponseCode\."
```

检测阈值：以上命令合计命中 >= 3 个定义 → 触发生成

### 查询模板生成规则

**分片键提取**（三级降级）：
1. 从 sharding 配置提取（精确）：`rg "shardingColumn|sharding-column" -t yaml -t xml`
2. 从注解提取：`rg "@ShardingKey" -t java`
3. 从字段命名推断：`seller_id`/`user_id`/`out_biz_no`

**索引提取**：
- 实体注解：`rg "@TableIndex|@Index" -t java`
- Mapper XML 高频条件：从 WHERE 子句统计最常用列

**SQL 模板生成约束**：
- 必须包含分片键条件
- 必须包含 LIMIT（默认 10）
- 使用 `SELECT *`（不指定列名）
- WHERE 条件优先使用索引列

### XRay 模板生成规则

| 深度 | 模板内容 |
|------|---------|
| standard | 3 种基础模板：按 TraceID、按错误、按业务单号 |
| deep | 基础模板 + 每条 L3 链路定制化查询（含入口方法关键词） |

**模板参数来源**：
- 服务名：L0 项目名称（subApplication）
- 业务单号字段：L5 核心表的 biz_no 类字段
- 链路入口方法：L3 核心链路的入口方法名

### 决策树生成规则

**检测条件**：deep 模式 + L4 异常策略 >= 3 种

**决策树结构**：
```
故障现象（从 L4.3 异常类型提取）
├── 检查步骤（XRay 查询 → DMS 查询 → 配置检查）
├── 分支判断（基于检查结果分支）
└── 修复方式（代码/配置/数据三类）
```

**关键**：使用文本格式树（非 Mermaid），原因：
- LLM 可直接解析和引用
- 可嵌入具体的 DMS/XRay 查询语句
- 支持多级嵌套和条件分支

详细模板参考 `references/table-templates.md` 和 `references/complete-template.md`。

### 数据库抽样验证方法论

> 通过实际 DMS 查询验证代码识别的 DB 表，发现空表、异常分布、枚举值不一致等问题。

**生成条件与深度**：

| 模式 | 行为 | 工具依赖 | 时间影响 |
|------|------|---------|---------|
| quick | 跳过 | -- | 无 |
| standard | 仅空表检测（`SELECT 1 FROM {table} LIMIT 1`） | xhs-tools DMS | +2 min |
| deep | 完整抽样（量级+枚举+状态分布） | xhs-tools DMS | +5 min |

**执行步骤**：

1. **获取核心表列表**：从 L5 @TableName/@Table 扫描结果获取
2. **确定抽样范围**：优先对 L3 数据流转涉及的表抽样（最多 15 条 SQL）
3. **提取分片键**：复用 L5.6 分片键提取结果
4. **执行抽样查询**（使用 xhs-tools `execute_dms_sql_query`）：
   - 空表检测：`SELECT 1 FROM {table} LIMIT 1`
   - 数据量估算：`SELECT COUNT(*) FROM {table} WHERE {shard_key} = ? LIMIT 1`
   - 枚举覆盖：`SELECT DISTINCT {enum_field} FROM {table} WHERE {shard_key} = ? LIMIT 50`
   - 状态分布：`SELECT {status_field}, COUNT(*) as cnt FROM {table} WHERE {shard_key} = ? GROUP BY {status_field} LIMIT 20`
5. **对比验证**：
   - 枚举值 vs 代码定义的 Enum 类 → 计算覆盖率
   - 中间态占比 → 判断是否有卡住风险
6. **产出 L5.7**：表级抽样结果 + 枚举覆盖验证 + 状态分布

**DMS 查询约束**（继承 xhs-tools 限制）：
- 必须包含分片键条件（空表检测除外）
- 必须包含 LIMIT
- 30s 超时，失败标记为"跳过"
- 使用 `project` 参数自动解析库名

### 字段类型检查方法论

> 对比 Java Entity 字段类型与 MySQL DDL 列类型，自动发现类型不匹配风险。

**生成条件**：deep 模式 + xhs-tools `get_cached_table_schema` 可用

**执行步骤**：

1. **获取 MySQL DDL**：对 L5 核心表调用 `get_cached_table_schema(table, project)`
2. **解析 Java Entity 字段**：
   - 扫描 DO 类字段定义（见 `references/code-patterns.md` Entity 字段类型提取）
   - 排除 `@TableField(exist = false)` 非 DB 字段
   - 映射 Java 字段名→DB 列名（camelCase→snake_case / @TableField 注解）
3. **逐字段类型比对**：
   - 按 `references/code-patterns.md` Java↔MySQL 类型映射规则评估风险
   - HIGH/MEDIUM/LOW 三级风险标记
4. **业务规则特检**：
   - 金额字段（字段名含 amount/fee/income/price/cost）：必须 Long/BigDecimal ↔ bigint/decimal
   - 分片键字段：必须 String ↔ varchar
   - ID 字段：必须 Long ↔ bigint
5. **产出 L5.8**：类型匹配结果（仅列风险项）+ 汇总统计 + 业务规则检查

**降级策略**：`get_cached_table_schema` 不可用时，跳过 L5.8 并在文档中说明原因。

---

## 可视化规范

### Mermaid 配色主题

```
primary   (#0969DA) - 入口/触发点
secondary (#54AEFF) - 主要处理
tertiary  (#B6E3FF) - 次要处理
success   (#1A7F37) - 正向/成功
warning   (#9A6700) - 警告/判断
error     (#CF222E) - 错误/逆向
highlight (#8250DF) - 核心节点
```

### 图表类型选择

| 场景 | 推荐图表 |
|------|---------|
| 系统边界 | graph TB（上下流向） |
| 业务场景分类 | graph TB（树形结构） |
| 业务流程 | graph LR（左右流向） |
| 技术调用 | sequenceDiagram（时序图） |
| 状态流转 | stateDiagram-v2 |
| 数据关系 | erDiagram |

---

## 输出要求

1. **业务导向**：先讲业务含义，再补充技术细节
2. **图文结合**：架构图建立直觉，表格补充细节
3. **代码定位**：引用代码使用 `file_path:line_number` 格式
4. **独立可读**：每章可独立阅读
5. **语言一致**：遵循项目现有语言风格
6. **精简高效**：表格优先，避免冗余描述

---

## 双文档交替驱动验证方法论（v4.0）

> 核心升级：从 v3.0 的单文档 RED/GREEN/REFACTOR 升级为双文档交替驱动 + 3 轮强制 + FK-first SQL。

### 双文档模型

```
分析文档: chains/{chain}-analysis.md     → 可修正，每轮后根据 FAIL 项更新
验证文档: verification/round-{N}.md      → 不可变，每轮独立生成
```

**交替驱动流程**:
```
Step 4 分析产出 → Round 1 验证 → 修正分析 → Round 2 验证 → 修正分析 → Round 3 验证 → 准出门禁
```

### FK 优先级层级

| 优先级 | FK 类型 | 说明 | 示例 |
|--------|---------|------|------|
| P1 | 列 FK | 两表同名列+索引 | `record_no = record_no` |
| P2 | JSON FK | ext/extra JSON 字段 | `ext→settlementRecordNo = record_no` |
| P3 | 跨模块列 FK | 不同命名同语义 | `command_no = request_no` |
| ⛔ | 泛化主键 | 禁止作为关联键 | `package_id` / `order_id` / `biz_no` |

### 3 轮强制验证

| 轮次 | 目标 | 输入 | 产出 |
|------|------|------|------|
| Round 1 | 初始验证，发现偏差 | Step 4 分析文档 | round-1-verification.md |
| Round 2 | 修正验证，确认修复 | R1 修正后分析文档 | round-2-verification.md |
| Round 3 | 全量回归，确保无退化 | R2 修正后分析文档 | round-3-verification.md |

### 准出门禁（4 条件）

```
rounds_completed == 3       AND
P0_assertions ALL PASS      AND
hop_pass_rate >= 90%         AND
fk_violation_count == 0
```

### 验证断言分类

| 类别 | 代码 | 验证内容 | 来源层级 | 验证工具 |
|------|------|---------|---------|---------|
| 拓扑 | V-TOPO | RPC 上下游关系 | L0 | batch_query_upstream/downstream |
| 入口 | V-ENTRY | 服务入口有流量 | L0 | query_rpc_topology |
| 数据 | V-DATA | 表存在且有数据 | L5 | execute_dms_sql_query |
| 关联 | V-REL | 表间关联正确 | L3/L5 | DMS join 查询 |
| 配置 | V-CFG | Apollo 配置正确 | L2/L6 | get_apollo_config_value |
| 流程 | V-FLOW | 业务流程可追踪 | L3/L4 | XRay + DMS |
| 状态 | V-STS | 状态机可观测 | L4 | DMS distinct status |
| 消息 | V-MQ | MQ 有消息流转 | L2 | query_mq_by_key |
| 调度 | V-JOB | Job 在运行 | L0 | list_jobs |

### 数据持久化

```
{project}/docs/arch-analysis/
├── collected-data/              # Step 1 & 3 采集数据
├── verification/                # 3 轮验证结果（不可修改）
│   ├── round-1-verification.md
│   ├── round-2-verification.md
│   ├── round-3-verification.md
│   └── graduation-report.md    # 准出报告
├── chains/                      # 按链路的分析文档（可修正）
│   ├── {chain}-analysis.md
│   └── README.md
└── analysis-meta.json           # 元数据（含轮次追踪）
```

详细验证方法论参考 `references/verification-guide.md`。
详细数据采集策略参考 `references/data-collection-guide.md`。
每轮验证文档模板参考 `references/verification-doc-template.md`。

---

## 参考材料

详细模板和示例请参考 `references/` 目录：
- `complete-template.md` - 完整文档模板
- `mermaid-templates.md` - Mermaid 图表模板库
- `table-templates.md` - 表格模板库
- `code-patterns.md` - 代码识别模式
- `traffic-guide.md` - 流量分析与核心链路识别指南
- `verification-guide.md` - 验证方法论（v3.0 新增）
- `verification-doc-template.md` - 每轮验证文档模板（v4.0 新增）
- `data-collection-guide.md` - 数据采集策略（v3.0 新增）
