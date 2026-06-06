#!/bin/bash

echo "=============================================="
echo "  地核多物理场耦合模拟平台 - 启动脚本"
echo "  Geodynamo Multi-Physics Simulation Platform"
echo "=============================================="
echo ""

echo "[1/3] 启动后端服务..."
cd "$(dirname "$0")"
source .env

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "后端服务已启动 (PID: $BACKEND_PID)"
echo "  后端地址: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""

sleep 3

echo "[2/3] 启动前端服务..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "正在安装前端依赖..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "前端服务已启动 (PID: $FRONTEND_PID)"
echo "  前端地址: http://localhost:5173"
echo ""

echo "[3/3] 服务启动完成！"
echo "=============================================="
echo "默认账户："
echo "  管理员: admin / admin123"
echo "  博士后: postdoc1 / postdoc123"
echo "  教授: professor1 / professor123"
echo "  地磁学家: geophysicist1 / geo123"
echo "  首席科学家: chief1 / chief123"
echo "  研究员: researcher1 / researcher123"
echo "=============================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait
