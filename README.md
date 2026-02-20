# Galay Blog

基于 Galay Framework 构建的个人技术博客系统，用于展示 Galay 系列开源项目。

## 项目结构

```
blog/
├── frontend/           # 前端静态页面
│   ├── css/           # 样式文件
│   ├── js/            # JavaScript 脚本
│   ├── index.html     # 首页
│   ├── projects.html  # 项目展示
│   ├── docs.html      # 文档中心
│   ├── blog.html      # 博客列表
│   ├── article.html   # 文章详情
│   ├── search.html    # 搜索页面
│   ├── login.html     # 登录页面
│   ├── register.html  # 注册页面
│   └── profile.html   # 个人中心
├── service/           # 服务目录
│   ├── backend/       # C++ 博客 API 服务
│   ├── static/        # 静态站点 + 反向代理
│   └── ai/            # AI 问答服务
└── docker-compose.yml # 容器编排（static + backend + ai）
```

## 技术栈

### 后端
- **galay-kernel**: 高性能 C++ 协程网络库
- **galay-http**: HTTP/WebSocket 协议库
- **C++23**: 协程、`std::expected`、concepts、ranges 等现代特性

### 前端
- **原生 HTML/CSS/JS**: 无框架依赖
- **响应式设计**: 支持移动端和桌面端
- **暗色主题**: 赛博朋克风格 UI

## 功能特性

### API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/projects` | GET | 获取项目列表 |
| `/api/projects/:id` | GET | 获取项目详情 |
| `/api/posts` | GET | 获取博客文章列表 |
| `/api/posts/:id` | GET | 获取文章详情 |
| `/api/docs` | GET | 获取文档列表 |
| `/api/docs/:id` | GET | 获取文档详情 |

### 前端功能
- 项目展示与详情查看
- 文档中心（快速开始、使用指南、API 参考）
- 博客文章列表与阅读
- 全局搜索（Ctrl+K 快捷键）
- 用户认证（登录/注册/个人中心）

## 快速开始

### 环境要求
- C++23 编译器 (GCC 13+, Clang 17+)
- CMake 3.20+
- galay-kernel 和 galay-http 已安装

### 编译运行

```bash
# 进入 API 服务目录
cd service/backend

# 编译
mkdir build && cd build
cmake ..
make -j$(nproc)

# 运行
./bin/backend-server -p 8080
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-h, --host` | 监听地址 | 0.0.0.0 |
| `-p, --port` | 监听端口 | 8080 |
| `-s, --static` | 静态文件目录 | disabled |

### 访问

启动后访问 http://localhost:8080

## Docker 部署

```bash
# 全服务 host 网络（Linux）
docker compose up -d
```

如果页面一直转圈，可先做连通性检查：

```bash
# 1) 检查 static 的代理路由是否生效
docker compose exec static sh -lc 'echo "$API_PROXY_ROUTES"'

# 2) host 模式：backend / ai 都应可访问
docker compose exec static sh -lc 'curl -m 3 -sv http://127.0.0.1:8080/api/health'
docker compose exec static sh -lc 'curl -m 3 -sv http://127.0.0.1:18000/health'

# 3) 查看三服务日志
docker compose logs --tail=200 static backend ai
tail -f service/static/logs/static-server.log
tail -f service/ai/logs/ai-service.log
```

## Kubernetes 部署

```bash
# 应用配置
kubectl apply -f service/backend/k8s/

# 查看状态
kubectl get pods -l app=backend-service
```

## 性能指标

基于 galay-kernel 的高性能特性：
- **QPS**: 313,841
- **吞吐量**: 153.24 MB/s
- **延迟 P99**: < 1ms

## 相关项目

- [galay-kernel](https://github.com/gzj-creator/galay-kernel) - 高性能 C++20 协程网络库
- [galay-http](https://github.com/gzj-creator/galay-http) - HTTP/WebSocket 协议库
- [galay-utils](https://github.com/gzj-creator/galay-utils) - C++20 工具库
- [galay-mcp](https://github.com/gzj-creator/galay-mcp) - MCP 协议库

## 许可证

MIT License
