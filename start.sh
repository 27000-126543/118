#!/bin/bash

echo "=============================================="
echo "  地核多物理场耦合模拟平台 - 启动脚本"
echo "  Geodynamo Multi-Physics Simulation Platform"
echo "=============================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-local}"

if [ "$MODE" = "docker" ]; then
    echo "[Docker 模式] 正在启动所有服务..."
    echo ""
    
    echo "[1/2] 构建并启动 Docker 容器..."
    docker-compose up -d --build
    
    echo ""
    echo "[2/2] 等待服务就绪..."
    sleep 10
    
    echo ""
    echo "=============================================="
    echo "服务启动完成！"
    echo "  前端地址: http://localhost:8080"
    echo "  后端地址: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
    echo ""
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
    echo "=============================================="
else
    echo "[本地模式] 正在启动所有服务..."
    echo ""
    
    echo "[1/3] 检查并安装后端依赖..."
    if [ ! -d "venv" ]; then
        echo "正在创建虚拟环境..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
    echo "后端依赖检查完成"
    echo ""
    
    echo "[2/3] 启动后端服务..."
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
    BACKEND_PID=$!
    echo "后端服务已启动 (PID: $BACKEND_PID)"
    echo "  后端地址: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
    echo "  日志文件: backend.log"
    echo ""
    
    sleep 3
    
    echo "[3/3] 启动前端服务..."
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        echo "正在安装前端依赖..."
        npm install
    fi
    
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "前端服务已启动 (PID: $FRONTEND_PID)"
    echo "  前端地址: http://localhost:5173"
    echo "  日志文件: frontend.log"
    cd ..
    echo ""
    
    echo "=============================================="
    echo "服务启动完成！"
    echo ""
    echo "默认账户："
    echo "  管理员: admin / admin123"
    echo "  博士后: postdoc1 / postdoc123"
    echo "  教授: professor1 / professor123"
    echo "  地磁学家: geophysicist1 / geo123"
    echo "  首席科学家: chief1 / chief123"
    echo "  研究员: researcher1 / researcher123"
    echo ""
    echo "按 Ctrl+C 停止所有服务"
    echo "=============================================="
    echo ""
    
    cleanup() {
        echo ""
        echo "正在停止服务..."
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
        echo "服务已停止"
        exit 0
    }
    
    trap cleanup INT TERM
    
    echo "后端健康检查..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
            echo "✅ 后端服务正常"
            break
        fi
        sleep 2
    done
    
    echo ""
    echo "按 Ctrl+C 退出，服务将继续在后台运行"
    echo "如需查看日志: tail -f backend.log 或 tail -f frontend.log"
    
    wait
fi
