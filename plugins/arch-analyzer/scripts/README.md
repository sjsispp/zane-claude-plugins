# RPC 依赖分析脚本

用于生成项目的 RPC 依赖分析数据，供 `/arch-analyze` 命令使用。

## 脚本列表

| 脚本 | 功能 | 输出 |
|------|------|------|
| `analyze-rpc-enhanced.py` | 静态代码分析 | `{project}/docs/rpc-analysis/{service}-enhanced.json` |
| `extract-rpc-methods.py` | 提取 RPC Server 方法 | `{project}/docs/rpc-analysis/{service}-methods.json` |
| `analyze-upstream.py` | 上游调用分析 | `{project}/docs/rpc-analysis/{service}-upstream.json` |
| `generate-deps-report.py` | 生成最终报告 | `{project}/docs/rpc-analysis/{service}-deps.json` |

## 快速使用

```bash
# 完整分析流程（假设项目路径为 /path/to/redsettlement）
SCRIPTS=~/.claude/plugins/local/arch-analyzer/scripts
PROJECT=/path/to/redsettlement

# Step 1: 静态分析
python3 $SCRIPTS/analyze-rpc-enhanced.py $PROJECT

# Step 2: 提取方法列表
python3 $SCRIPTS/extract-rpc-methods.py $PROJECT

# Step 3a: XRay 下游查询（使用 xhs-tools MCP 工具，见下方说明）

# Step 3b: 上游分析（生成查询任务）
python3 $SCRIPTS/analyze-upstream.py $PROJECT --generate-tasks
# 使用 xhs-tools MCP query_upstream_services 查询
# 整理结果到 {service}-upstream.json

# Step 4: 生成最终报告（自动合并 upstream 数据）
python3 $SCRIPTS/generate-deps-report.py $PROJECT
```

## Step 3a: XRay 下游数据查询

使用 xhs-tools MCP 工具获取"本服务调用谁"的流量数据：

```
query_downstream_services(
    app="{service}-service-default",
    service="{method-name}",
    edgeType="Service",
    days=14
)
```

将查询结果整理为 `{project}/docs/rpc-analysis/{service}-xray.json`

## Step 3b: XRay 上游数据查询

使用 xhs-tools MCP 工具获取"谁在调用本服务"的流量数据：

```
query_upstream_services(
    app="{service}-service-default",
    service="{method-name}",
    days=14
)
```

将查询结果整理为 `{project}/docs/rpc-analysis/{service}-upstream.json`：

```json
{
  "project": "{service}",
  "analysisType": "upstream",
  "analysisTime": "2026-01-28T12:00:00Z",
  "queryPeriod": "14 days",
  "appName": "{service}-service-default",
  "upstream": [
    {
      "targetMethod": "methodName",
      "callerApp": "caller-service",
      "callerMethod": "callerMethodName",
      "calls": "100 万",
      "avgLatency": "10.5ms"
    }
  ]
}
```

## 输出文件说明

| 文件 | 说明 | 保留 |
|------|------|------|
| `{service}-deps.json` | 最终依赖报告 | ✅ 必须 |
| `{service}-xray.json` | XRay 下游运行时数据 | ✅ 必须 |
| `{service}-upstream.json` | XRay 上游运行时数据 | ✅ 必须 |
| `{service}-methods.json` | RPC 方法列表 | 可选 |
| `{service}-enhanced.json` | 静态分析详情 | 自动清理 |

## 依赖

- Python 3.6+
- 无外部依赖（仅使用标准库）
