#!/bin/bash

echo "安装后端 Python 依赖..."
pip install -r requirements.txt

echo ""
echo "安装前端 Node.js 依赖..."
cd frontend
npm install

echo ""
echo "依赖安装完成！"
echo "使用 ./start.sh 启动平台"
