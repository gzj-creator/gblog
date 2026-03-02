# Business Service

`service/business` 提供博客内容业务接口（projects/posts/docs）。

## 主要接口

- `GET /api/health`
- `GET /api/projects`
- `GET /api/projects/:id`
- `GET /api/posts`
- `GET /api/posts/:id`
- `GET /api/docs`
- `GET /api/docs/:id`

> 认证接口由 `service/auth` 提供，网关转发路径为 `/api/v1/auth/*`。

## 构建

```bash
bash scripts/S3-Build.sh
```

## 运行

```bash
bash scripts/S1-RunServer.sh
```

或直接运行：

```bash
./build/bin/backend-server -h 0.0.0.0 -p 8080 -s ../../frontend
```
