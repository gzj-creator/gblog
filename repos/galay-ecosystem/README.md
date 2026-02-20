# Galay 生态文档汇聚与优化总结

> 本文档基于 `galay-*` 各仓库文档进行汇聚、去重与结构化重排，面向“选型 + 落地 + 运维”场景。

## 1. 生态总览

Galay 是以 C++23 协程为中心的网络与服务组件体系，核心价值是：

- 一致异步模型：统一 `co_await` 风格，降低多协议栈心智负担
- 分层可组合：运行时、传输层、协议层、数据客户端、工具层解耦
- 跨平台后端：围绕 `kqueue / epoll / io_uring` 的统一抽象
- 工程友好：`#include` 稳定路径优先，`import` 模块化路径可选增强

推荐按“先通链路，再做增强”推进：

1. `galay-kernel`（运行时）
2. `galay-http`（协议入口）或 `galay-rpc`（服务通信）
3. `galay-ssl`（安全）
4. `galay-redis/mysql/mongo/etcd`（状态与数据）
5. `galay-utils`（工程能力）
6. `galay-mcp`（AI 工具协议）

## 2. 架构分层（优化后的统一视图）

### 2.1 Runtime 层

- `galay-kernel`
- 职责：协程调度、事件循环、异步 IO 后端统一、Awaitable 基础设施
- 关键词：`Runtime`、`Scheduler`、`Coroutine`

### 2.2 Transport/Security 层

- `galay-ssl`
- 职责：TLS 上下文、握手、加密收发、关闭流程
- 关键词：`SslContext`、`SslSocket`、Memory BIO

### 2.3 Protocol/Service 层

- `galay-http`：HTTP/1.1、HTTP/2(h2c)、WebSocket、路由与静态文件
- `galay-rpc`：Unary/流式 RPC、服务注册发现抽象
- `galay-mcp`：MCP 协议（stdio/http）与工具注册

### 2.4 Data Access 层

- `galay-redis`：异步命令、Pipeline、连接池/拓扑扩展
- `galay-mysql`：异步/同步双路径、预处理、事务
- `galay-mongo`：CRUD + Pipeline + SCRAM-SHA-256
- `galay-etcd`：KV、Lease、Txn(PipelineOp)

### 2.5 Tooling/Foundation 层

- `galay-utils`
- 职责：线程池、熔断、负载均衡、字符串/随机/系统工具等工程能力

## 3. 模块能力汇总（去重后）

### 3.1 galay-kernel

- 定位：全栈协程运行时内核
- 核心能力：IO/Compute 调度解耦、多后端事件驱动、Awaitable 异步模型统一
- 适用场景：高并发网络服务底座、需要可控调度策略的系统服务

### 3.2 galay-ssl

- 定位：协程友好的 TLS 传输能力
- 核心能力：上下文与证书策略管理、异步握手/收发/关闭、与调度器解耦的 Memory BIO 管线
- 适用场景：HTTPS/WSS/RPC 加密通信、对握手时延与吞吐敏感的服务链路

### 3.3 galay-http

- 定位：通用 Web 协议栈与入口层
- 核心能力：`HttpServer + HttpRouter` 路由分发、`HttpClient + HttpSession` 请求链路、HTTP/1.1+HTTP/2(h2c)+WebSocket、静态资源挂载与反向代理
- 适用场景：API 网关、后台服务、静态站点托管

### 3.4 galay-rpc

- 定位：服务间协程 RPC 通信框架
- 核心能力：服务/方法注册与统一调用语义、Unary 与流式调用、服务发现抽象接口
- 适用场景：微服务内部通信、低延迟强类型接口场景

### 3.5 galay-redis

- 定位：高并发缓存与消息路径客户端
- 核心能力：异步命令调用与超时控制、Pipeline 批量提交降低 RTT、连接池与拓扑扩展能力
- 适用场景：热点缓存、计数、会话状态

### 3.6 galay-mysql

- 定位：关系型数据访问客户端
- 核心能力：同步/异步双接口、预处理语句、事务控制
- 适用场景：OLTP 业务数据访问、对一致性与事务语义敏感的链路

### 3.7 galay-mongo

- 定位：文档数据库客户端
- 核心能力：CRUD + Pipeline、BSON 文档构造与编解码、SCRAM-SHA-256 认证
- 适用场景：文档模型/灵活 schema 业务、高并发读写与聚合场景

### 3.8 galay-etcd

- 定位：配置与服务治理客户端
- 核心能力：KV / Lease / Txn、PipelineOp 组合事务、最近操作结果回读接口
- 适用场景：配置中心、服务发现、分布式协调

### 3.9 galay-utils

- 定位：工程基础能力库（偏 header-only）
- 核心能力：ThreadPool、CircuitBreaker（熔断）、LoadBalancer、字符串/系统/随机等通用工具
- 适用场景：跨服务复用的工程基础能力

### 3.10 galay-mcp

- 定位：AI Tool 调用协议层
- 核心能力：stdio/http 双传输、工具 schema 构建、协议序列化与解析
- 适用场景：Agent 工具化接入、本地/远程 MCP 服务统一封装

## 4. 选型建议（优化决策版）

### 4.1 Web API 服务

- 最小组合：`kernel + http + utils`
- 需 TLS：加 `ssl`
- 需缓存：加 `redis`
- 需事务数据：加 `mysql`

### 4.2 内部微服务通信

- 最小组合：`kernel + rpc + utils`
- 服务发现：加 `etcd`
- 安全通信：加 `ssl`

### 4.3 AI Agent 工具平台

- 最小组合：`kernel + mcp + http`
- 状态存储：加 `redis/mysql/mongo` 之一
- 外部能力编排：通过 `mcp` 工具路由整合

## 5. 构建与接入策略（统一规范）

### 5.1 代码接入策略

- 默认：`#include`，兼容性最高，建议生产默认采用
- 可选：C++23 `import`，在工具链满足时渐进启用
- 原则：同一项目允许 include/import 并存，不强制一次迁移

### 5.2 构建策略

- 生产默认：`Release`
- 先关闭不必要 `EXAMPLES/TESTS/BENCHMARKS`
- 明确 IO 后端策略（Linux 优先评估 `epoll/io_uring`）
- 回归路径：先单模块 smoke，再跨模块联调
- 协议层优先做端到端压测（HTTP/RPC）

## 6. 性能与稳定性优化清单

### 6.1 协程与调度

- 避免在协程链路里混入阻塞调用
- 将 IO 密集与计算密集任务拆分到不同调度器维度
- 优先以 Pipeline/批处理减少往返次数

### 6.2 协议与网络

- HTTP 路由前缀分组，减少深层匹配成本
- TLS 长连接复用优先，避免高频握手
- 对 RPC 流式场景显式设置超时与背压策略

### 6.3 数据访问

- Redis：高频读写优先 Pipeline
- MySQL：热点 SQL 优先预处理
- Mongo：批量操作优先 Pipeline
- etcd：组合写操作优先 Txn/PipelineOp

### 6.4 工程韧性

- 默认启用熔断与超时边界（`galay-utils`）
- 将重试策略与幂等语义绑定，避免放大故障
- 为关键接口维护最小可回滚配置

## 7. AI 检索友好组织建议

为提升 RAG 检索质量，建议按以下结构维护文档：

- 每个模块一份 `README.md`（定位 + 能力 + API + 示例）
- 一份总览文档（即本文）用于跨模块问题召回
- 每个模块保留“典型场景 + 不适用边界”小节
- 关键 API 保留最小代码段，减少冗长样板

建议目录：

```text
repos/
  galay-ecosystem/README.md      # 跨仓库汇聚总结（本文）
  galay-kernel/README.md
  galay-http/README.md
  ...
```

## 8. 快速结论

- `galay-kernel` 是全栈底座，先定它的调度与后端策略
- `http/rpc/mcp` 是三类上层入口，按业务通信模型二选一或组合
- `redis/mysql/mongo/etcd` 不是互斥关系，应按数据语义拆分职责
- `utils` 应作为统一工程规范层，不建议散落实现重复能力
- 文档建设建议采用“模块 README + 生态总览”双层结构，最利于团队协作与 AI 检索
