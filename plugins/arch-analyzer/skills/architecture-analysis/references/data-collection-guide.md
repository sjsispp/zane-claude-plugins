# 数据采集策略参考

> 本文件定义 `/arch-analyze` 的数据采集策略，供 Step 1 和 Step 3 使用。

---

## Step 1: 全量数据采集矩阵

### 采集清单

| 数据类型 | MCP 工具 | 查询模式 | 持久化文件 | 并发组 |
|---------|---------|---------|-----------|--------|
| RPC 上游 | batch_query_upstream | 按项目名查询 | topology.json | Agent 1 |
| RPC 下游 | batch_query_downstream | 按项目名查询 | topology.json | Agent 1 |
| 方法级流量 | query_rpc_topology | 按方法名查询 TOP 接口 | topology.json | Agent 1 |
| MQ 流量 | query_mq_by_key | 按项目配置的 topic 查询 | mq-traffic.json | Agent 2 |
| Job 信息 | list_jobs / list_all_jobs | 按项目名查询 | jobs.json | Agent 2 |
| 表结构 | get_cached_table_schema | 代码扫描到的所有 @TableName 表 | table-schemas.json | Agent 3 |
| Apollo 配置 | search_apollo_config + get_apollo_config_value | 按项目名搜索 + 逐个获取值 | apollo-configs.json | Agent 3 |

### 并发执行策略

```
Agent 1 — RPC 拓扑 + 方法级流量
  1. batch_query_upstream(app=项目名) → 上游列表
  2. batch_query_downstream(app=项目名) → 下游列表
  3. query_rpc_topology(app=项目名, service=TOP5方法) → 方法级流量
  4. 合并写入 topology.json

Agent 2 — MQ + Job
  1. 从代码扫描提取 topic 列表（@XhsConsumer, sendAsync 等）
  2. query_mq_by_key(topic=各topic) → MQ 流量
  3. list_jobs(app=项目名) → Job 列表
  4. 分别写入 mq-traffic.json, jobs.json

Agent 3 — DB 表结构 + Apollo 配置
  1. 代码扫描 @TableName/@Table → 表名列表
  2. get_cached_table_schema(table=各表名, project=项目名) → DDL
  3. search_apollo_config(app=项目名) → 配置 key 列表
  4. get_apollo_config_value(key=各key, env=prod) → 配置值
  5. 分别写入 table-schemas.json, apollo-configs.json
```

### 持久化 JSON Schema

#### topology.json

```json
{
  "project": "项目名",
  "collected_at": "ISO8601",
  "upstream": [
    {
      "callerApp": "服务名",
      "callerMethod": "方法名",
      "targetMethod": "本服务方法",
      "calls": 1234567,
      "avgLatency": 10.5
    }
  ],
  "downstream": [
    {
      "targetApp": "服务名",
      "interface": "接口名",
      "method": "方法名",
      "calls": 654321,
      "avgLatency": 20.3
    }
  ],
  "methodTraffic": [
    {
      "method": "方法名",
      "calls": 9999999,
      "avgLatency": 15.0,
      "errorRate": 0.01
    }
  ]
}
```

#### mq-traffic.json

```json
{
  "project": "项目名",
  "collected_at": "ISO8601",
  "topics": [
    {
      "topic": "topic名",
      "role": "producer|consumer",
      "tag": "tag模式",
      "messageCount": 12345,
      "codeLocation": "类名:行号"
    }
  ]
}
```

#### jobs.json

```json
{
  "project": "项目名",
  "collected_at": "ISO8601",
  "jobs": [
    {
      "name": "job名称",
      "cron": "cron表达式",
      "status": "running|stopped",
      "lastExecution": "ISO8601",
      "codeLocation": "类名:行号"
    }
  ]
}
```

#### table-schemas.json

```json
{
  "project": "项目名",
  "collected_at": "ISO8601",
  "tables": [
    {
      "tableName": "表名",
      "database": "库名",
      "entityClass": "Java类名",
      "shardingKey": "分片键",
      "columns": [
        {
          "name": "列名",
          "type": "MySQL类型",
          "nullable": true,
          "comment": "注释"
        }
      ],
      "indexes": ["索引名列表"]
    }
  ]
}
```

#### apollo-configs.json

```json
{
  "project": "项目名",
  "collected_at": "ISO8601",
  "env": "prod|beta|sit",
  "configs": [
    {
      "key": "配置key",
      "value": "配置值",
      "namespace": "命名空间",
      "type": "开关|阈值|策略|映射"
    }
  ]
}
```

---

## Step 3: 线上数据采集规则

### 采集触发条件

Step 3 在 Step 2（核心链路识别）用户确认后执行，对每个已确认的核心业务场景采集。

### 采集要求

| 维度 | 要求 | 说明 |
|------|------|------|
| DMS 记录数 | **>= 10 条/场景** | 覆盖正常、边缘、异常情况 |
| XRay trace | **>= 3 条/场景** | 成功 trace + 失败 trace + 边缘 trace |
| 数据多样性 | 覆盖主要状态 | 不能全是同一状态的记录 |

### 采集策略

#### DMS 数据采集

对每个核心场景:

1. **正常记录** (>= 5 条): 终态成功的完整数据
```sql
SELECT * FROM {core_table}
WHERE {shard_key} = '{value}'
  AND status = '{success_status}'
ORDER BY created_at DESC
LIMIT 5
-- project: {project}
```

2. **边缘记录** (>= 3 条): 中间态、特殊状态
```sql
SELECT * FROM {core_table}
WHERE {shard_key} = '{value}'
  AND status IN ({intermediate_statuses})
ORDER BY created_at DESC
LIMIT 3
-- project: {project}
```

3. **异常记录** (>= 2 条): 失败、超时、重试
```sql
SELECT * FROM {core_table}
WHERE {shard_key} = '{value}'
  AND status IN ({error_statuses})
ORDER BY created_at DESC
LIMIT 2
-- project: {project}
```

#### XRay trace 采集

对每个核心场景:

1. **成功 trace**: `{entryMethod} AND subApplication: {service} AND NOT level: ERROR`
2. **失败 trace**: `level: ERROR AND subApplication: {service} AND {entryMethod}`
3. **边缘 trace**: 按特殊关键词搜索（timeout, retry, duplicate 等）

### 持久化目录结构

```
collected-data/scenarios/
├── {scenario1}-data.json     # DMS 记录
├── {scenario1}-xray.json     # XRay trace
├── {scenario2}-data.json
├── {scenario2}-xray.json
└── ...
```

#### scenario-data.json schema

```json
{
  "scenario": "场景名",
  "collected_at": "ISO8601",
  "tables": {
    "表名": {
      "normal": [{"记录1"}, {"记录2"}],
      "edge": [{"记录"}],
      "error": [{"记录"}]
    }
  },
  "total_records": 15,
  "coverage": {
    "statuses_found": ["SUCCESS", "PROCESSING", "FAILED"],
    "statuses_expected": ["INIT", "PROCESSING", "SUCCESS", "FAILED"]
  }
}
```

#### scenario-xray.json schema

```json
{
  "scenario": "场景名",
  "collected_at": "ISO8601",
  "traces": [
    {
      "traceId": "xxx",
      "type": "success|error|edge",
      "entryMethod": "方法名",
      "duration": 150,
      "spans": 12,
      "summary": "一句话描述"
    }
  ]
}
```

---

## 逐跳 SQL 生成（v4.0 新增）

> 为双文档验证生成每一跳的 FK-first SQL。

### SQL 生成流程（per hop）

```
1. get_cached_table_schema(上游表, project) → 获取列名、索引
2. get_cached_table_schema(下游表, project) → 获取列名、索引
3. 识别 FK 字段:
   a. 查找两表同名列（优先有索引的）→ P1 列FK
   b. 上游表 ext/extra JSON 列包含下游 key → P2 JSON FK
   c. 代码搜索确认跨模块映射 → P3 跨模块FK
   d. 仅剩 package_id/order_id → ⛔ FORBIDDEN
4. 生成 SQL:
   SELECT * FROM {下游表}
   WHERE {fk_field} = '{上游值}'
     AND {shard_key} = '{shard_value}'
   LIMIT 10;
5. 添加注释: -- DB: {database} | 索引: {index}
```

### FK 发现策略

| 策略 | 条件 | 操作 | 示例 |
|------|------|------|------|
| 列FK | 两表存在同名列且有索引 | 直接用 | `record_no = record_no` |
| JSON FK | 上游表 ext/extra JSON 字段包含下游表 key | 提取 JSON 值 | `ext→settlementRecordNo = record_no` |
| 跨模块FK | 不同命名但语义相同 | 代码搜索确认 | `command_no ↔ request_no` |
| FORBIDDEN | package_id/order_id/biz_no 等泛化ID | 禁止作为关联键 | ⛔ 自动 FAIL |

### SQL 模板

```sql
-- [Step {N}] {上游表} → {下游表}
-- DB: {database} | 索引: {index} | FK: {fk_type}
SELECT * FROM {下游表}
WHERE {fk_field} = '{上游值}'
  AND {shard_key} = '{shard_value}'
LIMIT 10;
```

**分片键优先级**: sharding_key > seller_id > user_id > 无分片（非分片表）

### 跨步校验 SQL

**金额一致性**:
```sql
-- 校验 Step 0 与 Step N 金额一致
-- Step 0: settle_acceptance.amount
SELECT amount FROM {start_table} WHERE {pk} = '{value}';
-- Step N: settlement_record.amount
SELECT amount FROM {end_table} WHERE {pk} = '{value}';
```

**时序校验**:
```sql
-- 校验各跳 create_time 时序
SELECT '{step}' as step, create_time FROM {table} WHERE {pk} = '{value}'
UNION ALL
SELECT '{step}' as step, create_time FROM {table} WHERE {pk} = '{value}'
ORDER BY create_time;
```

---

## analysis-meta.json schema

> 元数据文件，记录分析进度和验证状态。

```json
{
  "project": "项目名",
  "projectPath": "/path/to/project",
  "version": "3.0.0",
  "mode": "data-driven",
  "depth": "standard",
  "iteration": 1,
  "startedAt": "ISO8601",
  "lastUpdated": "ISO8601",
  "steps": {
    "step1_collection": "completed|in_progress|pending",
    "step2_identification": "completed|in_progress|pending",
    "step3_sampling": "completed|in_progress|pending",
    "step4_analysis": "completed|in_progress|pending",
    "step5_verification": "completed|in_progress|pending",
    "step6_loop": "completed|in_progress|pending"
  },
  "layers_completed": ["L0", "L1", "L2"],
  "scenarios_confirmed": ["场景A", "场景B"],
  "scenarios_covered": ["场景A"],
  "verification": {
    "total": 0,
    "pass": 0,
    "fail": 0,
    "skip": 0,
    "pending": 0,
    "pass_rate": 0,
    "refactor_rounds": 0,
    "groups": {
      "G1": "pending",
      "G2": "pending",
      "G3": "pending",
      "G4": "pending",
      "G5": "pending"
    }
  },
  "tables_verified": [],
  "collected_data_files": [],
  "dual_doc": {
    "current_round": 0,
    "rounds": [],
    "graduation": {
      "status": "pending",
      "rounds_completed": 0,
      "p0_all_pass": false,
      "hop_rate": 0,
      "fk_compliant": false
    }
  }
}
```
