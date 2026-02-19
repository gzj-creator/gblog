cmake_minimum_required(VERSION 3.16)
project(galay-blog VERSION 1.0.0 LANGUAGES CXX)

# C++23 标准（依赖 std::expected）
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 编译选项
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")

# 平台检测
if(APPLE)
    add_definitions(-DUSE_KQUEUE)
    message(STATUS "Platform: macOS (using kqueue)")
elseif(UNIX)
    # 检查 io_uring 支持
    find_library(IOURING_LIB uring)
    if(IOURING_LIB)
        add_definitions(-DUSE_IOURING)
        message(STATUS "Platform: Linux (using io_uring)")
    else()
        add_definitions(-DUSE_EPOLL)
        message(STATUS "Platform: Linux (using epoll)")
    endif()
endif()

# 查找依赖库
find_package(PkgConfig QUIET)

# galay-kernel
find_library(GALAY_KERNEL_LIB galay-kernel HINTS /usr/local/lib)
if(NOT GALAY_KERNEL_LIB)
    message(FATAL_ERROR "galay-kernel library not found")
endif()
message(STATUS "Found galay-kernel: ${GALAY_KERNEL_LIB}")

# galay-http
find_library(GALAY_HTTP_LIB galay-http HINTS /usr/local/lib)
if(NOT GALAY_HTTP_LIB)
    message(FATAL_ERROR "galay-http library not found")
endif()
message(STATUS "Found galay-http: ${GALAY_HTTP_LIB}")

# 头文件路径
include_directories(
    /usr/local/include
)

# 输出目录
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# 主程序
add_executable(blog-server BlogServer.cc)
target_link_libraries(blog-server
    ${GALAY_HTTP_LIB}
    ${GALAY_KERNEL_LIB}
    pthread
)

# io_uring 链接
if(IOURING_LIB)
    target_link_libraries(blog-server ${IOURING_LIB})
endif()

# 测试程序
option(BUILD_TESTS "Build test programs" OFF)
if(BUILD_TESTS AND EXISTS ${CMAKE_SOURCE_DIR}/test)
    file(GLOB TEST_SOURCES "test/*.cc")
    foreach(TEST_SOURCE ${TEST_SOURCES})
        get_filename_component(TEST_NAME ${TEST_SOURCE} NAME_WE)
        add_executable(${TEST_NAME} ${TEST_SOURCE})
        target_link_libraries(${TEST_NAME}
            ${GALAY_HTTP_LIB}
            ${GALAY_KERNEL_LIB}
            pthread
        )
        if(IOURING_LIB)
            target_link_libraries(${TEST_NAME} ${IOURING_LIB})
        endif()
    endforeach()
endif()

# 安装
install(TARGETS blog-server DESTINATION bin)

# 打印配置信息
message(STATUS "============================================")
message(STATUS "Galay Blog Server Configuration")
message(STATUS "============================================")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "============================================")
