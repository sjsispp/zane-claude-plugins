---
name: generate-rpc-analysis
description: 为项目生成 RPC 依赖分析数据（deps.json + xray.json）
allowed_tools: Bash, Glob, Grep, Read, Write, Task, AskUserQuestion
arguments:
  - name: project
    description: "项目路径或名称（如 /path/to/redsettlement 或 redsettlement）"
    required: true
---

# 生成 RPC 依赖分析数据

为项目生成 `docs/rpc-analysis/{service}-deps.json` 文件，供 `/arch-analyze` 命令使用。

## 脚本位置

**插件内置脚本**：`${CLAUDE_PLUGIN_ROOT}/scripts/`

| 脚本 | 功能 |
|------|------|
| `analyze-rpc-enhanced.py` | Step 1: 静态分析，提取 RPC Client 依赖 |
| `extract-rpc-methods.py` | Step 2: 提取 RPC Server 方法列表 |
| `generate-deps-report.py` | Step 4: 合并数据生成最终报告 |

---

## 执行流程

### Step 1: 静态代码分析

**目的**: 从代码中提取 RPC Client 依赖配置和方法调用

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-rpc-enhanced.py $ARGUMENTS.project
```

**输出**: `{project}/docs/rpc-analysis/{service}-enhanced.json`（中间文件）

---

### Step 2: 提取 RPC Server 方法列表

**目的**: 获取服务暴露的所有 RPC 方法，用于 XRay 查询

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract-rpc-methods.py $ARGUMENTS.project
```

**输出**:
- 控制台打印方法列表
- `{project}/docs/rpc-analysis/{service}-methods.json`

---

### Step 3a: XRay 下游数据查询

**目的**: 获取"本服务调用谁"的方法级调用量

**使用 xhs-tools MCP 工具**，对每个方法执行：

```
query_downstream_services(
    app="{service}-service-default",
    service="{method-name}",
    edgeType="Service",
    days=14
)
```

**整理输出为** `{project}/docs/rpc-analysis/{service}-xray.json`

---

### Step 3b: XRay 上游数据查询（新增）

**目的**: 获取"谁在调用本服务"的调用量数据

**生成查询任务**：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-upstream.py $ARGUMENTS.project --generate-tasks
```

**使用 xhs-tools MCP 工具**，对每个 RPC Server 方法执行：

```
query_upstream_services(
    app="{service}-service-default",
    service="{method-name}",
    days=14
)
```

**整理输出为** `{project}/docs/rpc-analysis/{service}-upstream.json`：

```json
{
  "project": "{service}",
  "analysisType": "upstream",
  "analysisTime": "2026-01-28T12:00:00Z",
  "queryPeriod": "14 days",
  "appName": "{service}-service-default",
  "upstream": [
    {
      "targetMethod": "applySingleSettle",
      "callerApp": "luna-service-thirdparty",
      "callerMethod": "changeAmount",
      "calls": "1.15亿",
      "avgLatency": "205.97ms",
      "maxLatency": "5663ms",
      "errorCount": 0
    }
  ],
  "summary": {
    "totalMethods": 14,
    "methodsWithUpstream": 10,
    "totalCallers": 15,
    "topCallers": ["luna-service-thirdparty", "sellerstatementservice"]
  }
}
```

**注意**：
- 服务名通常是 `{service}-service-default`
- 低频接口（<10次/14天）可能无上游数据

---

### Step 4: 生成最终报告

**目的**: 合并静态分析与 XRay 数据，生成方法级依赖报告

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate-deps-report.py $ARGUMENTS.project
```

**输出**: `{project}/docs/rpc-analysis/{service}-deps.json`

---

## 最终报告格式

```json
{
  "project": "{service}",
  "timestamp": "2026-01-28",
  "dataSource": "static + xray(14 days + upstream)",
  "rpc": [
    { "app": "xxx", "service": "xxx-service-default", "interface": "XxxService", "method": "methodName", "calls": "100万" }
  ],
  "upstream": [
    { "targetMethod": "applySingleSettle", "callerApp": "luna-service-thirdparty", "callerMethod": "changeAmount", "calls": "1.15亿" }
  ],
  "selfCall": [
    { "service": "xxx-service-default", "interface": "XxxJobService", "method": "executeJob", "calls": "< 10" }
  ],
  "mq": [
    { "type": "producer", "topic": "xxx_topic", "calls": "50万" }
  ],
  "unused": [
    { "app": "xxx", "service": "xxx-service-default", "interface": "XxxService", "note": "已配置但代码中无调用" }
  ]
}
```

---

## 完整执行示例

```bash
# 假设项目在 /path/to/redsettlement

# Step 1: 静态分析
python3 ~/.claude/plugins/local/arch-analyzer/scripts/analyze-rpc-enhanced.py /path/to/redsettlement

# Step 2: 提取方法列表
python3 ~/.claude/plugins/local/arch-analyzer/scripts/extract-rpc-methods.py /path/to/redsettlement

# Step 3: XRay 查询（使用 xhs-tools MCP，对每个方法）
# ... 使用 query_downstream_services 工具 ...

# Step 4: 生成报告
python3 ~/.claude/plugins/local/arch-analyzer/scripts/generate-deps-report.py /path/to/redsettlement
```

---

## 文件说明

| 文件 | 说明 | 保留 |
|------|------|------|
| `{service}-deps.json` | 最终依赖报告 | ✅ 必须 |
| `{service}-xray.json` | XRay 运行时数据 | ✅ 必须 |
| `{service}-methods.json` | RPC 方法列表 | 可选 |
| `{service}-enhanced.json` | 静态分析详情 | 自动清理 |

---

开始为 `$ARGUMENTS.project` 生成 RPC 分析数据。
