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
├── backend/           # 后端服务
│   ├── BlogServer.cc  # 服务器主程序
│   ├── main.cc        # 入口文件
│   ├── CMakeLists.txt # 构建配置
│   └── docs/          # 后端文档
├── Dockerfile         # Docker 镜像构建
└── k8s/               # Kubernetes 配置
```

## 技术栈

### 后端
- **galay-kernel**: 高性能 C++20 协程网络库
- **galay-http**: HTTP/WebSocket 协议库
- **C++20**: 协程、concepts、ranges 等现代特性

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
- C++20 编译器 (GCC 11+, Clang 14+)
- CMake 3.20+
- galay-kernel 和 galay-http 已安装

### 编译运行

```bash
# 进入后端目录
cd backend

# 编译
mkdir build && cd build
cmake ..
make -j$(nproc)

# 运行
./blog-server -p 8080 -s ../../frontend
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-h, --host` | 监听地址 | 0.0.0.0 |
| `-p, --port` | 监听端口 | 8080 |
| `-s, --static` | 静态文件目录 | ../frontend |

### 访问

启动后访问 http://localhost:8080

## Docker 部署

```bash
# 构建镜像
docker build -t galay-blog:latest .

# 运行容器
docker run -d -p 8080:8080 galay-blog:latest
```

## Kubernetes 部署

```bash
# 应用配置
kubectl apply -f k8s/

# 查看状态
kubectl get pods -l app=blog-server
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
