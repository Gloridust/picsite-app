#!/bin/bash

# 安装依赖
pip install -r requirements.txt

# 清理旧的构建文件
rm -rf build dist

# 使用 pyinstaller 打包
pyinstaller picsite.spec

# 打包完成后的提示
echo "打包完成！可执行文件位于 dist/picsite.app" 