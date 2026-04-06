#!/bin/bash
# Stock Foker 启动脚本
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PID_DIR="$ROOT_DIR/.pids"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

echo "=== Stock Foker 启动 ==="

# ---------- 后端 ----------
echo ""
echo "[后端] 检查 Python 虚拟环境..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "[后端] 创建虚拟环境..."
    python3 -m venv "$BACKEND_DIR/venv"
fi

source "$BACKEND_DIR/venv/bin/activate"

# 检查依赖是否需要安装/更新
REQ_HASH=$(md5 -q "$BACKEND_DIR/requirements.txt" 2>/dev/null || md5sum "$BACKEND_DIR/requirements.txt" | cut -d' ' -f1)
CACHED_HASH=""
[ -f "$PID_DIR/.req_hash" ] && CACHED_HASH=$(cat "$PID_DIR/.req_hash")

if [ "$REQ_HASH" != "$CACHED_HASH" ]; then
    echo "[后端] 安装/更新依赖..."
    pip install -r "$BACKEND_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -q
    echo "$REQ_HASH" > "$PID_DIR/.req_hash"
else
    echo "[后端] 依赖已是最新"
fi

# 终止已有后端进程
if [ -f "$PID_DIR/backend.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/backend.pid")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[后端] 终止旧进程 (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

echo "[后端] 启动 FastAPI 服务 (端口 8000)..."
cd "$BACKEND_DIR"
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$PID_DIR/backend.pid"
echo "[后端] 已启动 (PID: $!)"

# ---------- 前端 ----------
echo ""
echo "[前端] 检查 node_modules..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "[前端] 安装依赖..."
    cd "$FRONTEND_DIR"
    npm install --registry https://registry.npmmirror.com
fi

# 检查 package.json 是否变更，需要重新安装
PKG_HASH=$(md5 -q "$FRONTEND_DIR/package.json" 2>/dev/null || md5sum "$FRONTEND_DIR/package.json" | cut -d' ' -f1)
CACHED_PKG_HASH=""
[ -f "$PID_DIR/.pkg_hash" ] && CACHED_PKG_HASH=$(cat "$PID_DIR/.pkg_hash")

if [ "$PKG_HASH" != "$CACHED_PKG_HASH" ] && [ -d "$FRONTEND_DIR/node_modules" ]; then
    echo "[前端] package.json 已变更，重新安装依赖..."
    cd "$FRONTEND_DIR"
    npm install --registry https://registry.npmmirror.com
fi
echo "$PKG_HASH" > "$PID_DIR/.pkg_hash"

# 终止已有前端进程
if [ -f "$PID_DIR/frontend.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/frontend.pid")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[前端] 终止旧进程 (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

echo "[前端] 启动 Vite 开发服务器 (端口 5173)..."
cd "$FRONTEND_DIR"
nohup npx vite --host 127.0.0.1 --port 5173 > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$PID_DIR/frontend.pid"
echo "[前端] 已启动 (PID: $!)"

# ---------- 等待就绪 ----------
echo ""
echo "等待服务就绪..."
for i in $(seq 1 10); do
    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo "[后端] 就绪"
        break
    fi
    sleep 1
done

for i in $(seq 1 10); do
    if curl -s http://127.0.0.1:5173/ > /dev/null 2>&1; then
        echo "[前端] 就绪"
        break
    fi
    sleep 1
done

echo ""
echo "=== 启动完成 ==="
echo "前端: http://127.0.0.1:5173"
echo "后端: http://127.0.0.1:8000"
echo "日志: $LOG_DIR/backend.log, $LOG_DIR/frontend.log"
