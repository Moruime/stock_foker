#!/bin/bash
# Stock Foker 终止脚本
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT_DIR/.pids"

echo "=== Stock Foker 终止 ==="

stopped=0

# 终止后端
if [ -f "$PID_DIR/backend.pid" ]; then
    PID=$(cat "$PID_DIR/backend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[后端] 终止进程 (PID: $PID)..."
        kill "$PID" 2>/dev/null
        stopped=$((stopped + 1))
    else
        echo "[后端] 进程已不存在"
    fi
    rm -f "$PID_DIR/backend.pid"
else
    echo "[后端] 无 PID 文件"
fi

# 终止前端
if [ -f "$PID_DIR/frontend.pid" ]; then
    PID=$(cat "$PID_DIR/frontend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[前端] 终止进程 (PID: $PID)..."
        kill "$PID" 2>/dev/null
        stopped=$((stopped + 1))
    else
        echo "[前端] 进程已不存在"
    fi
    rm -f "$PID_DIR/frontend.pid"
else
    echo "[前端] 无 PID 文件"
fi

# 兜底：清理残留端口占用
for port in 8000 5173; do
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "[清理] 端口 $port 仍有残留进程，强制终止..."
        echo "$pids" | xargs kill 2>/dev/null
        stopped=$((stopped + 1))
    fi
done

if [ $stopped -eq 0 ]; then
    echo "没有运行中的服务"
else
    echo ""
    echo "=== 全部已终止 ==="
fi
