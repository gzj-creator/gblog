#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

SRC="${SCRIPT_DIR}/main.cc"
OUT="${SCRIPT_DIR}/server"

HTTP_DIR="${GALAY_HTTP_DIR:-/Users/gongzhijie/Desktop/projects/git/galay-http}"
KERNEL_DIR="${GALAY_KERNEL_DIR:-/Users/gongzhijie/Desktop/projects/git/galay-kernel}"

HTTP_LIB_DIR="${GALAY_HTTP_LIB_DIR:-${HTTP_DIR}/build/galay-http}"
KERNEL_LIB_DIR="${GALAY_KERNEL_LIB_DIR:-${KERNEL_DIR}/build/lib}"

CXX="${CXX:-clang++}"
CXXFLAGS=("-std=c++23" "-O2")

INCLUDES=(
    "-I${HTTP_DIR}"
    "-I${KERNEL_DIR}"
)

find_lib() {
    local dir="$1"
    local name="$2"
    for ext in dylib so a; do
        local candidate="${dir}/lib${name}.${ext}"
        if [[ -f "${candidate}" ]]; then
            echo "${candidate}"
            return 0
        fi
    done
    return 1
}

HTTP_LIB="$(find_lib "${HTTP_LIB_DIR}" "galay-http" || true)"
KERNEL_LIB="$(find_lib "${KERNEL_LIB_DIR}" "galay-kernel" || true)"

if [[ -z "${HTTP_LIB}" ]]; then
    echo "[error] libgalay-http not found in ${HTTP_LIB_DIR}"
    echo "        Please build galay-http first or set GALAY_HTTP_LIB_DIR."
    exit 1
fi

if [[ -z "${KERNEL_LIB}" ]]; then
    echo "[error] libgalay-kernel not found in ${KERNEL_LIB_DIR}"
    echo "        Please build galay-kernel first or set GALAY_KERNEL_LIB_DIR."
    exit 1
fi

LIBS=()
RPATHS=()

if [[ "${HTTP_LIB}" == *.a ]]; then
    LIBS+=("${HTTP_LIB}")
else
    LIBS+=("-L${HTTP_LIB_DIR}" "-lgalay-http")
    RPATHS+=("${HTTP_LIB_DIR}")
fi

if [[ "${KERNEL_LIB}" == *.a ]]; then
    LIBS+=("${KERNEL_LIB}")
else
    LIBS+=("-L${KERNEL_LIB_DIR}" "-lgalay-kernel")
    RPATHS+=("${KERNEL_LIB_DIR}")
fi

if [[ -d "/opt/homebrew/lib" ]]; then
    if ls /opt/homebrew/lib/libspdlog.* >/dev/null 2>&1; then
        LIBS+=("-L/opt/homebrew/lib" "-lspdlog")
    fi
    if ls /opt/homebrew/lib/libssl.* >/dev/null 2>&1; then
        LIBS+=("-L/opt/homebrew/lib" "-lssl" "-lcrypto")
    fi
fi

if [[ -d "/usr/local/lib" ]]; then
    if ls /usr/local/lib/libspdlog.* >/dev/null 2>&1; then
        LIBS+=("-L/usr/local/lib" "-lspdlog")
    fi
    if ls /usr/local/lib/libssl.* >/dev/null 2>&1; then
        LIBS+=("-L/usr/local/lib" "-lssl" "-lcrypto")
    fi
fi

RPATH_FLAGS=()
if [[ "${#RPATHS[@]}" -gt 0 ]]; then
    for dir in "${RPATHS[@]}"; do
        RPATH_FLAGS+=("-Wl,-rpath,${dir}")
    done
fi

echo "[build] ${SRC} -> ${OUT}"
set -x
"${CXX}" "${SRC}" \
    "${CXXFLAGS[@]}" \
    "${INCLUDES[@]}" \
    "${LIBS[@]}" \
    -pthread \
    "${RPATH_FLAGS[@]}" \
    -o "${OUT}"
set +x

echo "[done] binary: ${OUT}"
