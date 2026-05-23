# 代码识别模式

> **重要**：本文件定义的代码扫描模式是**降级方案**。
>
> **优先使用预分析数据**：如果项目有 `docs/rpc-analysis/{service}-deps.json`，应直接读取，
> 包含静态分析 + XRay 运行时数据（14天流量），比代码扫描更准确。
>
> **推荐使用 ripgrep (rg)**：更快、更智能、自动忽略 .git/target 目录。

---

## RPC 依赖识别（优先方案）

### 读取预分析数据

**数据位置**：`{project}/docs/rpc-analysis/`

| 文件 | 内容 | 用途 |
|------|------|------|
| `{service}-deps.json` | RPC 依赖 + MQ + 流量数据 | **主要数据源** |
| `{service}-xray.json` | XRay 运行时详情 | 延迟、调用链 |

**deps.json 结构**：
```json
{
  "project": "redsettlement",
  "dataSource": "static + xray(14 days)",
  "rpc": [
    { "app": "redpaycore", "interface": "RedpayRoyaltyUnitService", "method": "applyFundRoyalty", "calls": "2.46亿" }
  ],
  "mq": [
    { "type": "producer", "topic": "redsettlement_settle_record_finish", "calls": "6094万" }
  ],
  "unused": [
    { "app": "redpaycore", "interface": "RedpayCashierPayService", "note": "已配置但代码中无调用" }
  ]
}
```

**检测逻辑**：
```
1. 识别项目名称（从 pom.xml 提取 artifactId）
2. 检查 {project}/docs/rpc-analysis/{service}-deps.json 是否存在
3. 存在 → 直接读取，跳过代码扫描
4. 不存在 → 使用下方的代码扫描降级方案
```

---

## 代码扫描（降级方案）

> 当没有 rpc-analysis 预分析数据时使用。

### RPC Server（提供 RPC 服务）

| 框架 | 识别模式 | 搜索命令 | 适用项目 |
|------|---------|---------|---------|
| Thrift | `implements XxxService.Iface` | `rg -t java "implements.*\.Iface"` | 小红书内部 |
| gRPC | `extends XxxGrpc.XxxImplBase` | `rg -t java "extends.*Grpc\..*ImplBase"` | 通用 |

**特征补充**：
- 方法第一个参数通常为 `Context context`
- 返回类型为 Thrift Response 对象（如 `XxxResponse`）
- 类名通常以 `Rpc`、`Server`、`ServiceImpl` 结尾

### MQ Consumer（消息消费者）

| 框架 | 识别模式 | 搜索命令 |
|------|---------|---------|
| 小红书 MQ | `@XhsConsumer` | `rg -t java "@XhsConsumer"` |
| RocketMQ | `@RocketMQMessageListener` | `rg -t java "@RocketMQMessageListener"` |
| Kafka | `@KafkaListener` | `rg -t java "@KafkaListener"` |

**关键属性提取**：
```bash
# 提取 topic、tag、consumerGroup
rg -t java "@XhsConsumer" -A 10 | rg 'topic\s*=\s*"([^"]+)"' -o -r '$1'
rg -t java "@XhsConsumer" -A 10 | rg 'tag\s*=\s*"([^"]+)"' -o -r '$1'
rg -t java "@XhsConsumer" -A 10 | rg 'consumerGroup\s*=\s*"([^"]+)"' -o -r '$1'
```

### HTTP 接口

| 框架 | 识别模式 | 搜索命令 |
|------|---------|---------|
| Spring MVC | `@RestController` / `@Controller` | `rg -t java "@RestController"` |
| 路由注解 | `@RequestMapping` / `@GetMapping` 等 | `rg -t java "@\w+Mapping"` |

**路径提取**：
```bash
# 提取类级路径
rg -t java "@RequestMapping" -A 1 | rg 'value\s*=\s*"([^"]+)"' -o -r '$1'

# 提取方法级路径
rg -t java "@(Get|Post|Put|Delete)Mapping" -B 2 -A 1
```

**环境标识**：
- `@Conditional(SitCondition.class)` 表示仅 SIT 环境可用
- `@Profile("test")` 表示测试环境专用

### 定时任务（JOB）

| 框架 | 识别模式 | 搜索命令 |
|------|---------|---------|
| Spring | `@Scheduled` | `rg -t java "@Scheduled"` |
| XXL-Job | `@XxlJob` | `rg -t java "@XxlJob"` |
| Elastic-Job | `@ElasticJobConf` | `rg -t java "@ElasticJobConf"` |

---

## 下游依赖识别

### RPC Client（调用外部 RPC 服务）

**配置方式**：
```java
// 方式1: ClientBuilder 构建
ClientBuilder.create(XxxService.Iface.class, "service-name")
    .withTimeout(1000)
    .buildStub()

// 方式2: 注解注入
@Resource
private XxxService.Iface xxxService;
```

| 识别模式 | 搜索命令 |
|---------|---------|
| `ClientBuilder.create` | `rg -t java "ClientBuilder\.create"` |
| `@Resource` + `.Iface` | `rg -t java "\.Iface\s"` |

**配置提取**：
```bash
# 提取服务名和超时配置
rg -t java "ClientBuilder\.create" -A 5 | rg 'create\(.*"([^"]+)"\)'
```

**调用特征**：
- `xxxService.method(ContextHelper.getContext(), request)`

### MQ Producer（消息发送）

| 框架 | 识别模式 | 搜索命令 |
|------|---------|---------|
| 小红书 Events | `Events.publish` / `Events.sendAsync` | `rg -t java "Events\.(publish\|sendAsync)"` |
| RocketMQ | `rocketMQTemplate.send` | `rg -t java "rocketMQTemplate\."` |
| Kafka | `kafkaTemplate.send` | `rg -t java "kafkaTemplate\."` |

### HTTP Client（调用外部 HTTP 服务）

| 框架 | 识别模式 | 搜索命令 |
|------|---------|---------|
| RestTemplate | `restTemplate.xxx` | `rg -t java "restTemplate\."` |
| Feign | `@FeignClient` | `rg -t java "@FeignClient"` |
| OkHttp | `OkHttpClient` | `rg -t java "OkHttpClient"` |

---

## 数据实体识别

### 数据库表映射

| ORM 框架 | 识别模式 | 搜索命令 |
|---------|---------|---------|
| MyBatis-Plus | `@TableName("xxx")` | `rg -t java "@TableName"` |
| JPA | `@Table(name = "xxx")` / `@Entity` | `rg -t java "@Table\|@Entity"` |

**表名提取**：
```bash
# 提取表名
rg -t java "@TableName" -A 1 | rg '@TableName\("([^"]+)"\)' -o -r '$1'
```

**字段映射提取**：
```bash
# 提取字段映射（MyBatis-Plus）
rg -t java "@TableField" -B 1 -A 1

# 识别非数据库字段
rg -t java '@TableField\(exist\s*=\s*false\)'
```

**提取信息**：
- 表名：从注解参数提取
- 实体类名：类声明
- 字段映射：`@TableField` / `@Column`

### Redis 缓存

| 识别模式 | 搜索命令 |
|---------|---------|
| `@Cacheable` | `rg -t java "@Cacheable"` |
| `RedisTemplate` | `rg -t java "RedisTemplate\|StringRedisTemplate"` |
| Caffeine | `Caffeine.newBuilder()` | `rg -t java "Caffeine\.newBuilder"` |
| Guava Cache | `CacheBuilder` | `rg -t java "CacheBuilder"` |

---

## 扩展模式

### 事务与并发

| 类型 | 识别模式 | 搜索命令 |
|------|---------|---------|
| 声明式事务 | `@Transactional` | `rg -t java "@Transactional"` |
| 分布式事务 (Seata) | `@GlobalTransactional` | `rg -t java "@GlobalTransactional"` |
| 异步方法 | `@Async` | `rg -t java "@Async"` |
| CompletableFuture | `CompletableFuture.supplyAsync` | `rg -t java "CompletableFuture"` |

### Spring Cloud 微服务

| 组件 | 识别模式 | 搜索命令 |
|------|---------|---------|
| 服务发现 | `@EnableDiscoveryClient` | `rg -t java "@EnableDiscoveryClient"` |
| OpenFeign | `@FeignClient(name = "xxx")` | `rg -t java "@FeignClient"` |
| 负载均衡 | `@LoadBalanced` | `rg -t java "@LoadBalanced"` |

---

## 扫描策略

### 并发扫描建议

```
Agent 1: 服务入口扫描
├── RPC Server (implements Iface)
├── MQ Consumer (@XhsConsumer/@RocketMQMessageListener)
├── HTTP Controller (@RestController)
└── JOB (@Scheduled/@XxlJob)

Agent 2: 下游依赖扫描
├── RPC Client (ClientBuilder / @Resource + Iface)
├── MQ Producer (Events.publish)
└── HTTP Client (@FeignClient/RestTemplate)

Agent 3: 数据实体扫描
├── DB Entity (@TableName/@Table)
├── 加载 rpc-analysis 流量数据
└── 关联表结构信息
```

### 排除规则

```bash
# 排除测试目录和生成代码
rg -t java "pattern" --glob '!**/test/**' --glob '!**/generated/**'

# 仅扫描 src/main
rg -t java "pattern" src/main
```

### 统计输出格式

```markdown
### 服务入口统计
| 类型 | 数量 | TOP3 接口 | 日均流量 |
|-----|------|----------|---------|
| RPC | 12 | settlement, query, batch | 2.46亿 |
| MQ | 3 | settle_topic | 6094万 |
| HTTP | 5 | /api/health, /test/* | - |
| JOB | 2 | syncJob, cleanJob | - |

### 下游依赖统计
| 类型 | 数量 | TOP3 依赖 |
|-----|------|----------|
| RPC | 15 | redaccountcore, redpaycore, userservice |
| MQ | 1 | settle_finish_topic |
| DB | 8 | t_settlement_record, t_royalty_record |
```

---

## 注意事项

1. **模式优先级**：先用精确模式（如注解），再用宽泛模式（如方法名）
2. **误报过滤**：排除 test 目录、generated 代码
3. **跨语言支持**：本模式主要针对 Java，其他语言需调整
4. **性能优化**：大项目建议限制搜索范围（如只扫描 src/main）
5. **点号转义**：正则中的 `.` 需要转义为 `\.`（如 `restTemplate\.`）

---

## 业务场景路由模式

> 识别系统中的多场景路由机制，用于支撑 L2 事件×场景矩阵的构建。

### 场景标识字段扫描

```bash
# 识别场景分发字段
rg "bizScene|bizIdentity|bizEvent" src/main --type java

# 识别场景枚举定义
rg "enum.*(Scene|Identity|Event|BizType)" src/main --type java

# 识别场景常量
rg "BIZ_SCENE_|SCENE_|IDENTITY_" src/main --type java
```

### 配置驱动分发扫描

```bash
# Apollo Map 配置（JSON Map 注入）
rg "@ApolloJsonValue.*Map" src/main --type java

# Apollo 场景级 namespace
rg "@ApolloJsonValue.*\{prefix\}.*\{scene\}" src/main --type java

# 策略工厂模式
rg "Map<String,.*Handler>|Factory.*get.*Handler" src/main --type java

# switch/case 场景分支
rg "switch.*bizScene|switch.*scene|case.*BIZ_SCENE" src/main --type java
```

### 配置数据获取

| 优先级 | 数据来源 | 路径/方法 |
|--------|---------|----------|
| 1 | Apollo 快照（本地） | `{project}/docs/config/apollo-config-*.json` |
| 2 | 已有配置分析文档 | `{project}/docs/config/*-对比分析.md` |
| 3 | MCP 工具实时获取 | `get_apollo_config_value(key, env)` |
| 4 | 代码逻辑推断 | 从默认值和注释推断配置含义 |

### 场景路由识别模式汇总

| 路由模式 | 代码特征 | 搜索命令 | 说明 |
|---------|---------|---------|------|
| Map 分发 | `Map<String, Handler>` | `rg "Map.*Handler" src/main` | 按 key 分发到不同处理器 |
| 工厂模式 | `Factory.getHandler(scene)` | `rg "Factory.*Handler" src/main` | 工厂创建场景处理器 |
| 配置驱动 | `@ApolloJsonValue` + Map | `rg "@ApolloJsonValue.*Map" src/main` | 配置值直接驱动分发 |
| 枚举分支 | `switch(bizScene)` | `rg "switch.*Scene" src/main` | 枚举值显式分支 |
| 条件匹配 | `MVEL expression` | `rg "effectiveConditions\|MVEL" src/main` | 表达式动态匹配 |

---

## 错误处理模式识别

> 用于 L4.4 错误码速查的自动扫描。检测到自定义错误码定义 >= 3 个时触发。

### 错误码定义扫描

| 扫描目标 | 识别特征 | 搜索命令 | 说明 |
|---------|---------|---------|------|
| 枚举错误码 | `enum XxxErrorCode` | `rg -t java "enum.*(Error\|Result\|Biz)Code"` | 枚举类集中定义错误码 |
| 常量错误码 | `static final String ERR_` | `rg -t java "(ERROR_CODE\|ERR_\|FAIL_).*="` | 常量类分散定义 |
| 自定义异常 | `extends BizException` | `rg -t java "class.*extends.*(Exception)"` | 业务异常类层次 |
| 响应码常量 | `ResultCode.XXX` | `rg -t java "ResultCode\.\|ResponseCode\."` | 统一响应码引用 |

### 错误码关联信息提取

```bash
# 提取错误码枚举值和描述
rg -t java "enum.*(Error|Result|Biz)Code" -A 30 | rg '^\s+\w+\(' -A 1

# 提取异常类的错误码引用
rg -t java "throw new.*Exception" -B 2 -A 1

# 提取错误码使用位置（触发场景）
rg -t java "ErrorCode\.\w+" --glob '!**/test/**'
```

### 检测条件

```
检测命令：rg -t java "enum.*(Error|Result|Biz)Code" --count
阈值：命中文件 >= 1 且枚举值定义 >= 3 个
满足 → 生成 L4.4 错误码速查
不满足 → 跳过
```

---

## 分片键识别

> 用于 L5.6 查询模板生成的分片键提取。DMS 查询必须包含分片键条件。

### 分片键来源

| 来源 | 搜索命令 | 说明 |
|------|---------|------|
| Sharding 配置 | `rg "sharding.key\|shardingKey\|sharding-key" -t java -t yaml -t xml` | MyHub/ShardingSphere 配置 |
| 实体注解 | `rg "@ShardingKey" -t java` | 自定义分片注解 |
| 命名推断 | 实体类中的 `seller_id` / `user_id` / `out_biz_no` | 常见分片键字段名 |
| 分片算法 | `rg "ShardingAlgorithm\|shardingColumn" -t java -t yaml -t xml` | 分片算法配置 |

### 分片键提取流程

```
1. 优先从 sharding 配置文件提取（精确）
   rg "shardingColumn\|sharding-column" -t yaml -t xml

2. 其次从注解提取
   rg "@ShardingKey" -t java -A 1

3. 最后从字段命名推断（常见模式）
   seller_id → 按商家分片（最常见）
   user_id → 按用户分片
   out_biz_no → 按业务单号分片
```

### 核心索引提取

```bash
# 从实体类中提取索引注解
rg -t java "@TableIndex\|@Index" -B 1 -A 3

# 从 Mapper XML 中提取常用查询条件（推断索引列）
rg "where.*=" -t xml --glob '*Mapper.xml' | rg -o '\w+\s*=' | sort | uniq -c | sort -rn | head -10
```

---

## Entity 字段类型提取

> 用于 L5.8 数据库字段类型检查的 Java Entity 字段解析。

### DO 类识别

| ORM 框架 | DO 类特征 | 搜索命令 |
|---------|---------|---------|
| MyBatis-Plus | `@TableName` + 字段定义 | `rg -t java "@TableName" -l` |
| JPA | `@Entity` / `@Table` | `rg -t java "@Entity\|@Table" -l` |

### 字段类型提取

```bash
# 提取 DO 类中所有字段定义（排除 static/transient）
rg -t java "private\s+(Long|Integer|String|BigDecimal|Date|LocalDateTime|Boolean)\s+\w+" --glob '*DO.java' --glob '*Entity.java'

# 提取 @TableField 映射关系
rg -t java "@TableField" -B 0 -A 2 --glob '*DO.java'

# 提取非数据库字段（需排除）
rg -t java '@TableField\(exist\s*=\s*false\)' --glob '*DO.java'
```

### 字段名→DB 列名映射规则

| Java 命名 | DB 列名 | 映射规则 |
|-----------|--------|---------|
| `sellerIncome` | `seller_income` | camelCase → snake_case（默认） |
| `bizNo` | `biz_no` | 自动转换 |
| `@TableField("custom_col")` | `custom_col` | 注解显式指定优先 |

---

## Java↔MySQL 类型映射规则

> 用于 L5.8 自动化类型检查。对比 Java Entity 字段类型与 MySQL 实际列类型，按风险等级报告不匹配项。

### 标准映射表

| Java 类型 | 期望 MySQL 类型 | 实际为其他类型时的风险 |
|-----------|---------------|-------------------|
| Long/long | bigint | int → **HIGH**（超 21 亿溢出） |
| Integer/int | int/tinyint/smallint | bigint → LOW（安全但浪费） |
| BigDecimal | decimal(M,N) | bigint → **HIGH**（精度丢失）；varchar → **MEDIUM** |
| String | varchar(N) | text → LOW（索引限制） |
| Date | datetime/timestamp | varchar → **MEDIUM**（不可索引排序） |
| LocalDateTime | datetime/timestamp | varchar → **MEDIUM** |
| Boolean/boolean | tinyint(1)/bit | int → LOW |

### 风险等级定义

| 风险 | 含义 | 触发条件 |
|------|------|---------|
| **HIGH** | 数据损坏/溢出风险 | Long↔int、BigDecimal↔bigint |
| **MEDIUM** | 功能受限风险 | Date↔varchar、精度不匹配 |
| **LOW** | 资源浪费 | Integer↔bigint |
| -- | 匹配正常 | 类型完全兼容 |

### 业务特殊规则（电商/支付领域）

| 规则 | Java 侧约束 | MySQL 侧约束 | 字段识别模式 |
|------|-----------|-------------|------------|
| 金额字段 | Long 或 BigDecimal | bigint 或 decimal | 字段名含 `amount/fee/income/price/cost` |
| 分片键字段 | String | varchar | 字段名为识别到的 sharding key |
| ID 字段 | Long | bigint | 字段名含 `_id` 后缀（排除 boolean 型） |
| 状态字段 | Integer 或 String | int/tinyint/varchar | 字段名含 `status/state/type` |

### 检测触发条件

```
前置条件：L5 检测到 @TableName/@Table（即存在 DB 实体）
工具依赖：xhs-tools get_cached_table_schema 可用（获取实际 DDL）
深度要求：deep 模式
不满足时：跳过 L5.8，不产出
```
