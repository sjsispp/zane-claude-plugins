# 流量分析与核心链路识别指南

> 本指南说明如何利用 rpc-analysis 数据识别核心业务和核心链路。

## 数据来源优先级

| 优先级 | 数据来源 | 说明 |
|--------|---------|------|
| **1** | `{project}/docs/rpc-analysis/` | 预分析数据（静态 + XRay 运行时） |
| 2 | 代码扫描 | 降级方案，参考 `code-patterns.md` |

**重要**：rpc-analysis 数据包含 14 天真实流量，比代码扫描更准确，应优先使用。

## 流量数据来源

### 数据目录结构

```
{project}/docs/rpc-analysis/
├── {service}-deps.json      # 依赖汇总（rpc/mq/unused）+ 流量数据
└── {service}-xray.json      # 运行时详情（callCount/avgLatency）
```

### deps.json 结构

```json
{
  "project": "redsettlement",
  "timestamp": "2026-01-28",
  "dataSource": "static + xray(14 days)",
  "rpc": [
    {
      "app": "redpaycore",
      "service": "redpaycore-service-defaultunit",
      "interface": "RedpayRoyaltyUnitService",
      "method": "applyFundRoyalty",
      "calls": "2.46亿"
    }
  ],
  "selfCall": [
    {
      "app": "redsettlement",
      "interface": "SettlementExecuteJobService",
      "method": "executeSettlementJob",
      "calls": "< 10"
    }
  ],
  "mq": [
    {
      "type": "producer",
      "topic": "redsettlement_settle_record_finish",
      "calls": "6094万"
    }
  ],
  "unused": [
    {
      "app": "redpaycore",
      "interface": "RedpayCashierPayService",
      "note": "已配置但代码中无调用"
    }
  ]
}
```

### 关键字段说明

| 字段 | 说明 | 用途 |
|------|------|------|
| `rpc` | 下游 RPC 依赖 | 依赖分析 |
| `selfCall` | 自调用（JOB 等） | 内部任务 |
| `mq` | MQ 生产者 | 消息依赖 |
| `unused` | 已配置但无调用 | 废弃接口识别 |
| `calls` | 14天调用量 | 流量量级评估 |

---

## 核心业务与核心链路识别

### 概念区分

| 层级 | 名称 | 说明 | 示例 |
|------|------|------|------|
| **核心业务** | Business | 业务领域，包含多条链路 | 结算业务、分账业务 |
| **核心链路** | Flow | 具体执行路径 | 正向结算、逆向结算 |

```
核心业务
├── 结算业务 (Settlement)
│   ├── 正向结算链路
│   ├── 逆向结算链路
│   └── 批量结算链路
└── 分账业务 (Royalty)
    ├── 申请分账链路
    └── 取消分账链路
```

### 核心业务识别

**评估维度**（权重）：

| 维度 | 权重 | 说明 |
|------|------|------|
| 流量量级 | 40% | 该业务下所有链路的流量总和 |
| 业务重要性 | 30% | 主流程 > 辅助流程 |
| 操作类型 | 20% | 写操作 > 读操作 |
| 复杂度 | 10% | 链路数量、依赖复杂度 |

**识别步骤**：

1. **聚合分析**：将相关 RPC 方法/MQ Topic 聚合为业务
2. **流量求和**：计算业务级总流量
3. **重要性评估**：结合操作类型、依赖链判断

### 业务聚合规则

按以下优先级将接口聚合为核心业务：

| 优先级 | 聚合方式 | 说明 | 示例 |
|--------|---------|------|------|
| 1 | **包结构聚合** | 同一业务包下的接口 | `com.xxx.settlement.*` → 结算业务 |
| 2 | **命名前缀聚合** | 同一命名前缀的方法 | `settlement*`, `batch*` → 结算业务 |
| 3 | **数据表聚合** | 操作同一核心表的接口 | 都操作 `t_settlement_record` |
| 4 | **业务语义聚合** | 业务领域相关性 | 需人工确认 |

**聚合示例**：
```
settlement、batchSettlement、reverseSettlement → 结算业务
applyRoyalty、cancelRoyalty、queryRoyalty → 分账业务
querySettlement、getSettlementDetail → 查询业务（或归入结算业务）
```

**业务边界判断**：

| 条件 | 处理方式 |
|------|---------|
| 接口同时涉及多个业务 | 归入主要业务，在备注中说明关联 |
| 查询接口 | 如仅服务于单一业务，归入该业务；否则独立为"查询业务" |
| 辅助接口（如健康检查） | 不计入核心业务 |

### 多场景方法识别

> 当一个 RPC 方法承载多个业务场景时（如 `executeCommand` 同时服务 DE/EE/C2C），需要特殊处理。

**识别信号**：

| 信号 | 检查方法 | 说明 |
|------|---------|------|
| 方法内场景分支 | 方法体内 switch/if on bizScene | 同一入口分流到不同处理逻辑 |
| 配置含多场景 key | Apollo 配置 `{prefix}.{sceneA}` / `{prefix}.{sceneB}` | 配置级多路径 |
| 多来源调用同方法 | 不同 MQ Tag 最终汇聚到同一方法 | 上游多源 → 单方法 |
| 下游按参数不同 | 同方法根据参数调用不同下游 | 运行时路径差异 |

**处理策略**：

| 策略 | 适用条件 | 说明 |
|------|---------|------|
| L3 标注"承载场景"列 | 所有多场景方法 | 在链路展示表中增加场景列 |
| L2 按事件×场景拆分 | 场景行为差异明显 | 在事件×场景矩阵中分别展示 |
| 合并相同行为场景 | 行为完全一致 | 避免过度拆分，标注"行为一致" |

### 业务重要性评估标准

**可量化的评估指标**：

| 指标 | 主流程 (10分) | 辅助流程 (5分) |
|------|-------------|-------------|
| 是否在主业务路径上 | 支付/结算/退款主链路 | 查询/统计/通知 |
| 是否涉及资金/库存变动 | 是 | 否 |
| 是否有 SLA 要求 | 有明确 SLA（如 P99 < 100ms） | 无或宽松 SLA |
| 故障影响范围 | 阻断核心业务 | 影响体验但不阻断 |
| 是否在监控告警中 | 核心监控指标 | 次要或无监控 |

**评分规则**：满足 3 项及以上 → 主流程(10分)，否则 → 辅助流程(5分)

### 核心链路识别

**评估维度**（权重）：

| 维度 | 权重 | 说明 |
|------|------|------|
| 流量量级 | 40% | 从 rpc-analysis 数据获取 |
| 操作类型 | 30% | 写操作 > 读操作 |
| 入口类型 | 20% | RPC/MQ > HTTP > JOB |
| 业务重要性 | 10% | 主流程 > 辅助 |

**计算公式**：
```
链路评分 = 流量分(40%) + 操作分(30%) + 入口分(20%) + 重要性分(10%)

流量分：
  > 1亿: 40分
  > 1000万: 30分
  > 100万: 20分
  > 10万: 10分
  其他: 5分

操作分：
  写操作(create/update/delete): 30分
  读操作(query/get/list): 15分

入口分：
  RPC Server: 20分
  MQ Consumer: 18分
  HTTP Controller: 10分
  JOB: 8分

重要性分（人工评估）：
  主流程: 10分
  辅助流程: 5分
```

---

## 交互确认流程

### 第零步：确认业务场景

> 在展示核心业务之前，先确认系统的业务场景划分。仅在识别到多场景系统时执行。

使用 `AskUserQuestion` 展示识别到的场景列表：

```markdown
基于代码扫描和配置分析，识别到以下业务场景：

| # | 场景标识 | 场景名称 | 识别来源 |
|---|---------|---------|---------|
| 1 | BIZ_SCENE_DE | 电商 | Apollo 配置 + 枚举类 |
| 2 | BIZ_SCENE_EE | 跨境电商 | Apollo 配置 + 枚举类 |
| 3 | BIZ_SCENE_C2C | C2C | Apollo 配置 |

选项：
1. 确认以上场景列表（推荐）
2. 补充遗漏的场景
3. 无多场景区分（跳过场景分析）
```

### 第一步：展示核心业务候选

使用 `AskUserQuestion` 让用户确认核心业务：

```markdown
基于流量和业务分析，识别到以下核心业务：

| # | 核心业务 | 包含链路数 | 14天总流量 | 评估 |
|---|---------|-----------|-----------|------|
| 1 | 结算业务 | 3 | 3.2亿 | ★★★ |
| 2 | 分账业务 | 2 | 1.5亿 | ★★★ |
| 3 | 查询业务 | 4 | 800万 | ★★ |

选项：
1. 确认 1,2 为核心业务（推荐）
2. 自定义选择（输入编号）
3. 全部分析
4. 跳过核心业务分析
```

### 第二步：展示核心链路候选

确认核心业务后，展示其下的核心链路：

```markdown
【结算业务】下识别到以下链路：

| # | 链路名称 | 入口 | 14天流量 | 承载场景 | 操作类型 | 评估 |
|---|---------|-----|---------|---------|---------|------|
| 1.1 | 正向结算 | RPC: settlement | 2.46亿 | DE/EE/C2C | 写 | ★★★ |
| 1.2 | 逆向结算 | RPC: reverseSettlement | 5600万 | DE/EE/C2C | 写 | ★★★ |
| 1.3 | 批量结算 | RPC: batchSettlement | 1800万 | 写 | ★★ |

【分账业务】下识别到以下链路：

| # | 链路名称 | 入口 | 14天流量 | 承载场景 | 操作类型 | 评估 |
|---|---------|-----|---------|---------|---------|------|
| 2.1 | 申请分账 | RPC: applyRoyalty | 1.17亿 | DE/EE | 写 | ★★★ |
| 2.2 | 取消分账 | RPC: cancelRoyalty | 3300万 | DE/EE | 写 | ★★ |

选项：
1. 分析 1.1, 1.2, 2.1（高流量链路，推荐）
2. 分析所有写操作链路
3. 自定义选择（输入编号）
4. 跳过链路深度分析
```

---

## 链路深度分析

### 分析内容

确认核心链路后，对每条链路进行深度分析：

| 分析项 | 输出格式 | 控制要求 |
|--------|---------|---------|
| 基本信息 | 表格 | 入口、流量、耗时、依赖 |
| 业务流程图 | Mermaid flowchart | 5-8 个节点（复杂链路可分层） |
| 数据流转表 | 表格 | 表名、操作、核心字段 |
| 状态机 | Mermaid stateDiagram | 仅有明确状态变化时 |
| 异常处理 | 表格 | 异常类型、处理策略、重试 |
| 核心代码 | 表格 | 类、方法、行号、职责 |

### 状态机展示条件

满足以下任一条件时绘制状态机：
1. 有显式的状态字段（如 status, state）且状态 >= 3 种
2. 有状态流转表或状态枚举定义
3. 有状态相关的业务规则（如：状态 A 不能直接转到状态 C）

不绘制状态机的情况：
- 只有成功/失败两种终态
- 状态是瞬态，不持久化

### 输出示例

```markdown
### 核心业务: 结算业务

#### 1.1 链路: 正向结算

##### 基本信息

| 维度 | 内容 |
|------|------|
| 入口 | RPC: SettlementService.settlement |
| 14天流量 | 2.46亿次 |
| 平均耗时 | 45ms (P99: 120ms) |
| 超时配置 | 3000ms |
| 触发条件 | 订单完成 + 结算开关开启 |
| 依赖服务 | redaccountcore, redpaycore |

##### 业务流程

​```mermaid
graph LR
    A([请求]) --> B[参数校验]
    B --> C[计算结算金额]
    C --> D{分账?}
    D -->|是| E[创建分账单]
    D -->|否| F[直接结算]
    E --> F
    F --> G[调用账户]
    G --> H([完成])
​```

##### 数据流转

| 表 | 操作 | 核心字段 | 说明 |
|---|------|---------|-----|
| t_settlement_record | INSERT | id, biz_no, status, amount | 创建结算单 |
| t_royalty_record | INSERT | id, settle_id, ratio | 创建分账记录（如有） |
| t_account_change | UPDATE | balance | 更新账户余额 |

##### 状态流转

​```mermaid
stateDiagram-v2
    [*] --> INIT: 创建
    INIT --> PROCESSING: 开始处理
    PROCESSING --> SUCCESS: 结算成功
    PROCESSING --> FAILED: 结算失败
    FAILED --> INIT: 重试
    SUCCESS --> [*]
​```

##### 异常处理

| 异常类型 | 处理策略 | 重试次数 | 代码位置 |
|---------|---------|---------|---------|
| 账户不存在 | 返回错误码 | 0 | SettlementService:78 |
| 余额不足 | 业务异常 | 0 | AccountService:156 |
| RPC超时 | 自动重试 | 3次 | RpcClient:45 |

##### 核心代码

| 阶段 | 类 | 方法 | 行号 | 职责 |
|------|---|------|-----|------|
| 入口 | SettlementRpcServer | settlement | 45 | 参数校验、调用业务层 |
| 业务 | SettlementManager | process | 120 | 业务编排 |
| 核心 | SettlementService | execute | 88 | 核心逻辑 |
| 分账 | RoyaltyService | apply | 156 | 分账处理 |
```

---

## 流量数据加载

### 检测与加载逻辑

```
1. 识别项目名称（从 pom.xml/build.gradle 提取 artifactId）
2. 构建数据路径：{project}/docs/rpc-analysis/{service}-deps.json
3. 检查文件是否存在
4. 存在则加载并解析
5. 不存在则主动触发分析生成数据

if (file.exists(depsJsonPath)) {
    loadTrafficData();
} else {
    // 主动生成数据
    generateRpcAnalysisData();
    loadTrafficData();
}
```

### 无数据时的主动生成策略

当项目目录下没有 rpc-analysis 数据时，**主动调用 xhs-tools 生成**：

| 步骤 | 工具 | 说明 |
|------|------|------|
| 1 | `query_downstream_services` | 获取下游 RPC/DB/Redis/MQ 依赖 |
| 2 | `query_upstream_services` | 获取上游调用方（流量来源） |
| 3 | `query_rpc_topology` | 获取具体方法的调用量和延迟 |
| 4 | 组装保存 | 生成 `{service}-deps.json` 文件 |

**生成的数据结构**：
```json
{
  "project": "redsettlement",
  "timestamp": "2026-01-28",
  "dataSource": "xray(14 days) - auto generated",
  "rpc": [
    { "app": "redpaycore", "interface": "XxxService", "method": "xxx", "calls": "2.46亿" }
  ],
  "mq": [
    { "type": "producer", "topic": "xxx_topic", "calls": "6094万" }
  ],
  "upstream": [
    { "app": "order-service", "interface": "SettlementService", "method": "settle", "calls": "2.46亿" }
  ]
}
```

**前置条件**：
- 项目需在 xhs-tools 中配置（可通过 `list_projects` 查看）
- 如未配置，提示用户添加项目配置或降级到代码扫描

### 最终降级策略

仅当 xhs-tools 无法获取数据时（如项目未配置、网络异常），才使用代码扫描：

| 识别方式 | 替代策略 |
|---------|---------|
| 流量量级 | 标记为"未知"，基于代码复杂度排序 |
| 核心业务 | 基于包结构、命名推断（如 core/main） |
| 核心链路 | 基于方法数量、注释标注识别 |

---

## 注意事项

1. **两层结构**：务必区分核心业务（领域）和核心链路（执行路径）
2. **用户确认**：核心业务和链路识别后必须交互确认，避免遗漏
3. **精简输出**：每条链路分析控制在半页内，突出核心信息
4. **数据时效**：rpc-analysis 数据有时效性，注意检查 analyzedAt 时间
5. **增量更新**：支持后续补充分析其他链路
