# 运行仿真平台
# 使用方法: .\run_simulation.ps1

Write-Host "启动视觉伺服控制系统仿真..." -ForegroundColor Green
Write-Host ""

# 检查 simulation.exe 是否存在
if (-not (Test-Path ".\simulation.exe")) {
    Write-Host "错误: 找不到 simulation.exe" -ForegroundColor Red
    exit 1
}

# 检查 main.py 是否存在
if (-not (Test-Path ".\main.py")) {
    Write-Host "错误: 找不到 main.py" -ForegroundColor Red
    exit 1
}

# 使用虚拟环境中的 Python 运行 main.py
$pythonPath = ".\.venv\Scripts\python.exe"

# 如果虚拟环境不存在，使用系统 Python
if (-not (Test-Path $pythonPath)) {
    Write-Host "警告: 虚拟环境不存在，使用系统 Python" -ForegroundColor Yellow
    $pythonPath = "python"
}

# 运行仿真平台
Write-Host "执行命令: .\simulation.exe $pythonPath main.py" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止运行"
Write-Host "=" * 60
Write-Host ""

.\simulation.exe $pythonPath main.py
