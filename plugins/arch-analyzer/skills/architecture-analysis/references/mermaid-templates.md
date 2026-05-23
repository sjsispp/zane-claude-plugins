# Mermaid 图表模板库

## 配色主题

```
classDef primary fill:#0969DA,stroke:#0550AE,stroke-width:1px,color:#FFFFFF
classDef secondary fill:#54AEFF,stroke:#218BFF,stroke-width:1px,color:#FFFFFF
classDef tertiary fill:#B6E3FF,stroke:#54AEFF,stroke-width:1px,color:#24292F
classDef light fill:#DDF4FF,stroke:#B6E3FF,stroke-width:1px,color:#24292F
classDef success fill:#1A7F37,stroke:#116329,stroke-width:1px,color:#FFFFFF
classDef warning fill:#9A6700,stroke:#7D4E00,stroke-width:1px,color:#FFFFFF
classDef error fill:#CF222E,stroke:#A40E26,stroke-width:1px,color:#FFFFFF
classDef neutral fill:#6E7781,stroke:#57606A,stroke-width:1px,color:#FFFFFF
classDef highlight fill:#8250DF,stroke:#6639BA,stroke-width:1px,color:#FFFFFF
```

## 颜色语义规范

| 样式类 | 语义 | 使用场景 |
|--------|------|---------|
| `primary` | 入口/触发点 | MQ消息、RPC入口、起始节点 |
| `secondary` | 主要处理 | 核心服务、业务逻辑 |
| `tertiary` | 次要处理 | 辅助服务、工具类 |
| `success` | 正向/成功 | 正向流程、成功状态 |
| `warning` | 警告/判断 | 条件分支、待处理 |
| `error` | 错误/逆向 | 逆向流程、失败状态 |
| `highlight` | 核心节点 | 关键组件、重点标注 |

---

## 系统边界图

```mermaid
graph TB
    classDef self fill:#8250DF,stroke:#6639BA,stroke-width:2px,color:#FFFFFF
    classDef upstream fill:#54AEFF,stroke:#218BFF,stroke-width:1px,color:#FFFFFF
    classDef downstream fill:#1A7F37,stroke:#116329,stroke-width:1px,color:#FFFFFF

    subgraph "上游系统"
        U1[系统1]:::upstream
        U2[系统2]:::upstream
    end

    subgraph "本系统"
        S[系统名称]:::self
    end

    subgraph "下游系统"
        D1[系统1]:::downstream
        D2[系统2]:::downstream
    end

    U1 -->|"MQ"| S
    U2 -->|"RPC"| S
    S -->|"RPC"| D1
    S -->|"MQ"| D2
```

---

## 分层架构图

```mermaid
graph TB
    classDef facade fill:#0969DA,stroke:#0550AE,stroke-width:1px,color:#FFFFFF
    classDef biz fill:#54AEFF,stroke:#218BFF,stroke-width:1px,color:#FFFFFF
    classDef core fill:#8250DF,stroke:#6639BA,stroke-width:1px,color:#FFFFFF
    classDef dal fill:#1A7F37,stroke:#116329,stroke-width:1px,color:#FFFFFF
    classDef integration fill:#6E7781,stroke:#57606A,stroke-width:1px,color:#FFFFFF

    subgraph "Facade 入口层"
        F1[MQ Consumer]:::facade
        F2[RPC Server]:::facade
    end

    subgraph "Biz 业务层"
        B1[Manager]:::biz
    end

    subgraph "Core 核心层"
        C1[Service]:::core
        C2[Handler]:::core
    end

    subgraph "DAL 数据层"
        D1[DAO]:::dal
    end

    subgraph "Integration 集成层"
        I1[RPC Client]:::integration
    end

    F1 --> B1
    F2 --> B1
    B1 --> C1
    C1 --> C2
    C1 --> D1
    C2 --> I1
```

---

## 业务场景树

```mermaid
graph TB
    classDef root fill:#0969DA,stroke:#0550AE,stroke-width:2px,color:#FFFFFF
    classDef category fill:#54AEFF,stroke:#218BFF,stroke-width:1px,color:#FFFFFF
    classDef scene fill:#B6E3FF,stroke:#54AEFF,stroke-width:1px,color:#24292F

    A[全部业务场景]:::root
    B[正向场景]:::category
    C[逆向场景]:::category

    B1[场景1]:::scene
    B2[场景2]:::scene
    C1[场景3]:::scene
    C2[场景4]:::scene

    A --> B
    A --> C
    B --> B1
    B --> B2
    C --> C1
    C --> C2
```

---

## 业务流程图（左右流向）

```mermaid
graph LR
    classDef primary fill:#0969DA,stroke:#0550AE,stroke-width:1px,color:#FFFFFF
    classDef process fill:#54AEFF,stroke:#218BFF,stroke-width:1px,color:#FFFFFF
    classDef success fill:#1A7F37,stroke:#116329,stroke-width:1px,color:#FFFFFF

    A([触发]):::primary
    B[步骤1]:::process
    C[步骤2]:::process
    D[步骤3]:::process
    E([完成]):::success

    A --> B --> C --> D --> E
```

---

## 时序图

```mermaid
sequenceDiagram
    autonumber
    participant 触发源
    participant 入口层
    participant 业务层
    participant 核心层
    participant 外部服务

    Note over 触发源,外部服务: 阶段一：接收请求
    触发源->>入口层: 业务事件
    入口层->>业务层: 转发处理

    Note over 触发源,外部服务: 阶段二：业务处理
    业务层->>核心层: 核心逻辑
    核心层->>外部服务: 外部调用
    外部服务-->>核心层: 返回结果

    Note over 触发源,外部服务: 阶段三：完成处理
    核心层-->>业务层: 处理完成
    业务层-->>入口层: 返回结果
```

---

## 状态机

```mermaid
stateDiagram-v2
    [*] --> INIT: 创建
    INIT --> PROCESSING: 开始处理
    INIT --> CANCELLED: 取消
    PROCESSING --> SUCCESS: 成功
    PROCESSING --> FAILED: 失败
    FAILED --> PROCESSING: 重试
    SUCCESS --> [*]
    CANCELLED --> [*]
```

---

## ER 图

```mermaid
erDiagram
    MAIN_TABLE ||--o{ SUB_TABLE : "包含"
    MAIN_TABLE ||--|| RELATED_TABLE : "关联"

    MAIN_TABLE {
        bigint id PK "主键"
        varchar biz_no UK "业务单号"
        varchar status "状态"
        json detail "详情"
        datetime create_time "创建时间"
    }

    SUB_TABLE {
        bigint id PK "主键"
        varchar main_biz_no FK "主表单号"
        varchar type "类型"
        bigint amount "金额"
    }
```

---

## 配置与行为映射图

```mermaid
graph LR
    classDef code fill:#0969DA,stroke:#0550AE,stroke-width:1px,color:#FFFFFF
    classDef config fill:#9A6700,stroke:#7D4E00,stroke-width:1px,color:#FFFFFF
    classDef result fill:#1A7F37,stroke:#116329,stroke-width:1px,color:#FFFFFF

    A[通用代码逻辑]:::code
    B[配置A: 场景1]:::config
    C[配置B: 场景2]:::config
    D[配置C: 场景3]:::config
    E[业务行为1]:::result
    F[业务行为2]:::result
    G[业务行为3]:::result

    A --> B --> E
    A --> C --> F
    A --> D --> G
```

---

## 七层递进框架图

```mermaid
graph TB
    classDef layer0 fill:#CF222E,stroke:#A40E26,stroke-width:2px,color:#FFFFFF
    classDef layer1 fill:#0969DA,stroke:#0550AE,stroke-width:2px,color:#FFFFFF
    classDef layer2 fill:#54AEFF,stroke:#218BFF,stroke-width:1px,color:#FFFFFF
    classDef layer3 fill:#8250DF,stroke:#6639BA,stroke-width:1px,color:#FFFFFF
    classDef layer4 fill:#1F6FEB,stroke:#0550AE,stroke-width:1px,color:#FFFFFF
    classDef layer5 fill:#1A7F37,stroke:#116329,stroke-width:1px,color:#FFFFFF
    classDef layer6 fill:#9A6700,stroke:#7D4E00,stroke-width:1px,color:#FFFFFF

    L0[L0: 服务全景<br/>入口/依赖/流量]:::layer0
    L1[L1: 项目概览<br/>What & Why]:::layer1
    L2[L2: 业务全景<br/>Business Scope]:::layer2
    L3[L3: 核心链路<br/>Core Flows]:::layer3
    L4[L4: 技术流程<br/>Technical Workflows]:::layer4
    L5[L5: 数据模型<br/>Data Model]:::layer5
    L6[L6: 配置与扩展<br/>Config & Extension]:::layer6

    L0 -->|"入口和依赖是什么？"| L1
    L1 -->|"系统是什么？"| L2
    L2 -->|"支持哪些业务？"| L3
    L3 -->|"核心业务如何流转？"| L4
    L4 -->|"技术如何实现？"| L5
    L5 -->|"数据如何存储？"| L6
```
