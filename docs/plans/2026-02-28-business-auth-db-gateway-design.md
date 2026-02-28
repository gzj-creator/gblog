# Business/Auth/DB/Gateway 服务拆分与 REST 重构设计

## 背景

当前项目中 `backend` 同时承担内容接口、认证逻辑、用户数据存储逻辑，职责耦合较重；`static` 既做静态资源托管也做网关代理。

本次目标是一次性完成：

1. 独立进程拆分（`business -> auth -> db`）
2. 对外 REST API 一次性重构为 `/api/v1/*`
3. 目录与服务命名同步迁移（`backend -> business`，`static -> gateway`）
4. `db service` 先落地 MySQL Adapter（`galay-mysql`），后续可扩展其他数据库

## 已确认决策

1. 进程通信：HTTP JSON（后续可迁移 HTTP/2）
2. 调用链：`business -> auth -> db`
3. 对外认证路径：`/api/v1/auth/*`
4. 内部 DB API 采用动作命名风格（如 `/api/v1/db/users/create`）
5. 密码策略：前端传 `password_b64`，后端 Base64 解码后使用 `salt + hash` 存储
6. refresh token 不持久化，重启后失效
7. 向量数据库暂不迁移，AI 仍使用 Chroma 落盘；DB 仅预留扩展接口

## 目标架构

### 服务与职责

1. `gateway`（原 `service/static`）
- 静态资源托管
- 反向代理路由
- 不承载业务逻辑

2. `business`（原 `service/backend`）
- 对外唯一 BFF
- 提供内容类 REST 接口
- 对接 `auth` 完成认证相关能力转发

3. `auth`（`service/auth`）
- 认证领域逻辑（注册、登录、刷新、登出、用户资料/密码/通知）
- 密码学处理（Base64 decode、salt 生成、哈希）
- 调用 `db` 完成用户数据读写

4. `db`（`service/db`）
- 数据访问抽象层
- 当前仅 `MySQLAdapter`（基于 `galay-mysql`）
- 屏蔽上层与具体数据库差异

## API 设计

### 对外 API（gateway -> business）

统一前缀：`/api/v1`

#### 内容资源

- `GET /api/v1/health`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `GET /api/v1/posts`
- `GET /api/v1/posts/{id}`
- `GET /api/v1/docs`
- `GET /api/v1/docs/{id}`

#### 认证与用户

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `PUT /api/v1/auth/profile`
- `PUT /api/v1/auth/password`
- `PUT /api/v1/auth/notifications`
- `DELETE /api/v1/auth/account`

### 内部 API（business/auth/db）

#### business -> auth

前缀建议：`/internal/v1/auth/*`，语义与对外 `/api/v1/auth/*` 一致。

#### auth -> db

动作风格前缀：`/api/v1/db/users/*`

- `POST /api/v1/db/users/create`
- `GET /api/v1/db/users/get-by-username/{username}`
- `GET /api/v1/db/users/get/{id}`
- `PATCH /api/v1/db/users/update/{id}`
- `PUT /api/v1/db/users/update-password/{id}`
- `PUT /api/v1/db/users/update-notifications/{id}`
- `DELETE /api/v1/db/users/delete/{id}`

## 数据模型（MySQL 首版）

### 表：`users`

- `id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT`
- `username VARCHAR(64) NOT NULL UNIQUE`
- `email VARCHAR(255) NOT NULL UNIQUE`
- `display_name VARCHAR(128) NOT NULL DEFAULT ''`
- `bio TEXT NOT NULL`
- `website VARCHAR(255) NOT NULL DEFAULT ''`
- `github VARCHAR(255) NOT NULL DEFAULT ''`
- `password_salt VARCHAR(64) NOT NULL`
- `password_hash VARCHAR(128) NOT NULL`
- `created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`
- `updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`

### 表：`user_notification_settings`

- `user_id BIGINT UNSIGNED PRIMARY KEY`
- `email_notifications TINYINT(1) NOT NULL DEFAULT 1`
- `new_post_notifications TINYINT(1) NOT NULL DEFAULT 1`
- `comment_reply_notifications TINYINT(1) NOT NULL DEFAULT 1`
- `release_notifications TINYINT(1) NOT NULL DEFAULT 1`
- `updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

## 密码与 Token 处理

### 密码

1. 客户端提交 `password_b64`
2. `auth` 使用 `galay-utils` Base64 进行解码
3. `auth` 生成随机盐值并计算哈希
4. `db` 仅持久化 `password_salt` 与 `password_hash`

### Token

1. `access_token` + `refresh_token` 由 `auth` 签发
2. `refresh_token` 仅内存维护
3. 服务重启后 refresh 失效，需重新登录

## 网关与端口规划

1. `gateway`：80
2. `business`：8080
3. `auth`：8081
4. `db`：8082
5. `ai`：8000

代理规则：

1. `/api/v1/* -> business:8080`
2. `/ai/* -> ai:8000`

## 重命名与迁移范围

1. 目录重命名：
- `service/backend -> service/business`
- `service/static -> service/gateway`

2. compose 重命名：
- service 名、container 名、volume 挂载路径、启动命令同步替换

3. 脚本与文档：
- 根 README、服务 README、脚本、构建说明、k8s 清单中的旧名替换

4. 前端 API 常量：
- `API_BASE` 统一 `/api/v1`
- `AUTH_API` 统一 `/api/v1/auth`

## 分阶段实施顺序

1. 先实现 `db`（MySQL Adapter + 用户相关 REST）
2. 实现 `auth`（密码/token/调用 db）
3. 改造 `business`（对外 `/api/v1`，内部调用 auth）
4. 改造 `gateway` 代理规则
5. 最后执行目录改名、compose 与文档收口

## 风险与缓解

1. 风险：一次性改名 + 拆服务导致启动链路中断
- 缓解：按阶段提交，逐步可运行验证

2. 风险：前端路径变更造成页面认证流断裂
- 缓解：统一替换 API 常量并对登录/刷新/me 做冒烟验证

3. 风险：MySQL 接入初期 schema 不一致
- 缓解：提供 init SQL 与启动前检查

4. 风险：refresh token 内存策略导致重启后体验变化
- 缓解：文档明确说明，前端收到 401 自动回登录

## 验收标准

1. 四服务可独立启动并可通过 gateway 联通
2. `/api/v1/auth/*` 与内容接口可用
3. 用户数据在 MySQL 可读写，密码为 `salt+hash` 持久化
4. 文档与脚本中不再出现旧主路径 `service/backend`、`service/static`（仅历史说明除外）
5. AI 服务继续使用 Chroma 落盘，不受本次改造影响

