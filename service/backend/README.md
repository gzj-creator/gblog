# Galay Blog 后端服务器

基于 galay-http 框架实现的个人博客后端服务器。

## 功能特性

- **静态文件服务**: 使用 galay-http 的静态文件挂载功能，支持 AUTO 传输模式
- **RESTful API**: 提供项目信息查询接口
- **高性能**: 基于 C++20 协程的异步架构

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/projects` | 获取所有项目列表 |
| GET | `/api/projects/:id` | 获取单个项目详情 |

## 构建

### 依赖

- C++23 编译器 (GCC 13+, Clang 17+)
- CMake 3.16+
- galay-kernel
- galay-http

### 编译

```bash
# 使用脚本构建
./scripts/S3-Build.sh

# 或手动构建
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DGALAY_KERNEL_BACKEND=epoll
make -j$(nproc)
```

## 运行

```bash
# 使用脚本运行
./scripts/S1-RunServer.sh

# 或直接运行
./build/bin/backend-server -p 8080 -s ../../frontend
```

### 命令行参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `-h, --host` | 服务器地址 | 0.0.0.0 |
| `-p, --port` | 服务器端口 | 8080 |
| `-s, --static` | 静态文件目录 | disabled |

## 测试

```bash
# 运行测试
./scripts/S2-RunTests.sh
```

## 导出二进制（Docker）

```bash
bash scripts/builder.sh
```

等价命令：

```bash
docker buildx build \
  --build-arg STATIC_BASE_IMAGE=ubuntu-24.04:galay-web-1.0 \
  --build-arg GALAY_KERNEL_BACKEND=epoll \
  --target artifact \
  --output type=local,dest=/home/ubuntu/service/gblob/service/backend/bin \
  -f docker/Dockerfile \
  .
```

## 项目结构

```text
service/backend/
├── BlogServer.cc       # 主程序
├── CMakeLists.txt      # 构建配置
├── docker/             # Docker 构建文件
├── README.md           # 项目说明
├── todo/               # 待办列表
├── docs/               # 文档
├── test/               # 测试代码
│   └── T1-BlogServerApi.cc
└── scripts/            # 脚本
    ├── S1-RunServer.sh
    ├── S2-RunTests.sh
    └── S3-Build.sh
```

## 许可证

MIT License
