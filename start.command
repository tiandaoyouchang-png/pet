#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
    echo "首次运行：正在创建虚拟环境（约 1 分钟）..."
    python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip -q
fi
echo "正在检查依赖..."
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/python pixar_pet.py
