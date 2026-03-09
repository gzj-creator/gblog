cmake_minimum_required(VERSION 3.16)

project(auth-server LANGUAGES CXX)

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

add_executable(auth-server
    AuthServer.cc
    src/DbHttpClient.cc
    src/PasswordCodec.cc
    src/TokenStore.cc
)

target_link_libraries(auth-server
    PRIVATE
        GalayHttp::GalayHttp
        spdlog::spdlog
        OpenSSL::Crypto
        Threads::Threads
)

if(GALAY_KERNEL_BACKEND STREQUAL "epoll")
    target_compile_definitions(auth-server PRIVATE USE_EPOLL)
elseif(GALAY_KERNEL_BACKEND STREQUAL "io_uring")
    target_compile_definitions(auth-server PRIVATE USE_IOURING)
elseif(GALAY_KERNEL_BACKEND STREQUAL "kqueue")
    target_compile_definitions(auth-server PRIVATE USE_KQUEUE)
elseif(GALAY_KERNEL_BACKEND STREQUAL "iocp")
    target_compile_definitions(auth-server PRIVATE USE_IOCP)
elseif(GALAY_KERNEL_BACKEND STREQUAL "auto")
    message(STATUS "GALAY_KERNEL_BACKEND=auto (no explicit backend macro)")
else()
    message(FATAL_ERROR "Unsupported GALAY_KERNEL_BACKEND: ${GALAY_KERNEL_BACKEND}")
endif()

install(TARGETS auth-server RUNTIME DESTINATION bin)
