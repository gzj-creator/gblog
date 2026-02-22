# Parser 模块

## 概述

Parser 模块提供了配置文件解析功能，支持INI格式和环境变量格式。

## 主要功能

### 配置文件解析

```cpp
ConfigParser config;

std::string content = R"(
[database]
host = localhost
port = 5432
name = "test_db"

[server]
port = 8080
debug = true
)";

config.parseString(content);

// 获取值
auto host = config.getValue("database.host");
int port = config.getValueAs<int>("database.port", 0);
```

### 环境变量解析

```cpp
EnvParser env;

std::string envContent = R"(
DATABASE_URL=postgres://localhost/db
export API_KEY=secret123
DEBUG=true
)";

env.parseString(envContent);

auto url = env.getValue("DATABASE_URL");
auto key = env.getValue("API_KEY");
```
