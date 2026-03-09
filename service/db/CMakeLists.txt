cmake_minimum_required(VERSION 3.16)

project(db-server LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

set(GALAY_KERNEL_BACKEND "auto" CACHE STRING "Kernel backend macro: auto|epoll|io_uring|kqueue|iocp")
set_property(CACHE GALAY_KERNEL_BACKEND PROPERTY STRINGS auto epoll io_uring kqueue iocp)

find_package(Threads REQUIRED)
find_package(spdlog REQUIRED)
find_package(galay-kernel REQUIRED)
find_package(GalayHttp REQUIRED)
find_package(OpenSSL REQUIRED)

if(NOT GalayMysql_DIR AND EXISTS "/usr/local/lib/cmake/galay-mysql/GalayMysqlConfig.cmake")
    set(GalayMysql_DIR "/usr/local/lib/cmake/galay-mysql")
endif()
find_package(GalayMysql CONFIG REQUIRED)

add_executable(db-server
    DbServer.cc
    src/MySqlDbProvider.cc
)

target_link_libraries(db-server
    PRIVATE
        GalayHttp::GalayHttp
        spdlog::spdlog
        galay-mysql::galay-mysql
        Threads::Threads
)

if(GALAY_KERNEL_BACKEND STREQUAL "epoll")
    target_compile_definitions(db-server PRIVATE USE_EPOLL)
elseif(GALAY_KERNEL_BACKEND STREQUAL "io_uring")
    target_compile_definitions(db-server PRIVATE USE_IOURING)
elseif(GALAY_KERNEL_BACKEND STREQUAL "kqueue")
    target_compile_definitions(db-server PRIVATE USE_KQUEUE)
elseif(GALAY_KERNEL_BACKEND STREQUAL "iocp")
    target_compile_definitions(db-server PRIVATE USE_IOCP)
elseif(GALAY_KERNEL_BACKEND STREQUAL "auto")
    message(STATUS "GALAY_KERNEL_BACKEND=auto (no explicit backend macro)")
else()
    message(FATAL_ERROR "Unsupported GALAY_KERNEL_BACKEND: ${GALAY_KERNEL_BACKEND}")
endif()

install(TARGETS db-server RUNTIME DESTINATION bin)
