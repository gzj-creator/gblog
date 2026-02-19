cmake_minimum_required(VERSION 3.16)

project(backend-server LANGUAGES CXX)

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

add_executable(backend-server BlogServer.cc)
target_link_libraries(backend-server
    PRIVATE
        GalayHttp::GalayHttp
        Threads::Threads
)

if(GALAY_KERNEL_BACKEND STREQUAL "epoll")
    target_compile_definitions(backend-server PRIVATE USE_EPOLL)
elseif(GALAY_KERNEL_BACKEND STREQUAL "io_uring")
    target_compile_definitions(backend-server PRIVATE USE_IOURING)
elseif(GALAY_KERNEL_BACKEND STREQUAL "kqueue")
    target_compile_definitions(backend-server PRIVATE USE_KQUEUE)
elseif(GALAY_KERNEL_BACKEND STREQUAL "iocp")
    target_compile_definitions(backend-server PRIVATE USE_IOCP)
elseif(GALAY_KERNEL_BACKEND STREQUAL "auto")
    message(STATUS "GALAY_KERNEL_BACKEND=auto (no explicit backend macro)")
else()
    message(FATAL_ERROR "Unsupported GALAY_KERNEL_BACKEND: ${GALAY_KERNEL_BACKEND}")
endif()

option(BUILD_TESTS "Build backend tests" OFF)
if(BUILD_TESTS AND EXISTS ${CMAKE_SOURCE_DIR}/test)
    file(GLOB TEST_SOURCES "${CMAKE_SOURCE_DIR}/test/*.cc")
    foreach(TEST_SOURCE IN LISTS TEST_SOURCES)
        get_filename_component(TEST_NAME "${TEST_SOURCE}" NAME_WE)
        add_executable(${TEST_NAME} "${TEST_SOURCE}")
        target_link_libraries(${TEST_NAME}
            PRIVATE
                GalayHttp::GalayHttp
                Threads::Threads
        )

        if(GALAY_KERNEL_BACKEND STREQUAL "epoll")
            target_compile_definitions(${TEST_NAME} PRIVATE USE_EPOLL)
        elseif(GALAY_KERNEL_BACKEND STREQUAL "io_uring")
            target_compile_definitions(${TEST_NAME} PRIVATE USE_IOURING)
        elseif(GALAY_KERNEL_BACKEND STREQUAL "kqueue")
            target_compile_definitions(${TEST_NAME} PRIVATE USE_KQUEUE)
        elseif(GALAY_KERNEL_BACKEND STREQUAL "iocp")
            target_compile_definitions(${TEST_NAME} PRIVATE USE_IOCP)
        endif()
    endforeach()
endif()

install(TARGETS backend-server RUNTIME DESTINATION bin)
