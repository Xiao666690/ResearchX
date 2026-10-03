# PaperAgent 一键启动脚本（Windows PowerShell）
# 用法：右键"使用 PowerShell 运行"，或在 PowerShell 中执行  .\start_all.ps1
# 说明：基于脚本自身所在目录定位前后端，压缩解压到任意路径均可启动。
$ErrorActionPreference = "Stop"

# ---- 路径定位（相对脚本目录，不写死盘符）----
$root = $PSScriptRoot
$bk   = Join-Path $root "PaperQuery_Backend"
$ft   = Join-Path $root "PaperQuery_Frontend"
$py   = Join-Path $bk ".venv\Scripts\python.exe"

# ---- 前置自检 ----
$missing = @()

if (-not (Test-Path -LiteralPath $py)) {
    $missing += "后端 Python 环境 .venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath (Join-Path $bk ".env"))) {
    $missing += "后端配置 PaperQuery_Backend\.env（可从 .env.example 复制并填入 API Key）"
}
if (-not (Test-Path -LiteralPath (Join-Path $bk "models\bge-m3"))) {
    Write-Host "== 未安装 BGE-M3，混合检索将降级为基础检索 ==" -ForegroundColor Yellow
}
if (-not (Test-Path -LiteralPath (Join-Path $bk "models\bge-reranker-v2-m3"))) {
    Write-Host "== 未安装 Reranker，重排功能将暂不可用 ==" -ForegroundColor Yellow
}

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    $missing += "Node.js（请安装 https://nodejs.org 后重试）"
}
if (-not (Test-Path -LiteralPath (Join-Path $ft "node_modules"))) {
    $missing += "前端依赖 node_modules（请先在 PaperQuery_Frontend 目录执行 npm install）"
}

if ($missing.Count -gt 0) {
    Write-Host "== 启动前发现以下缺失项 ==" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  [x] $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "请补齐上述依赖后重新运行本脚本。" -ForegroundColor Red
    exit 1
}

# ---- 端口占用检测 ----
function Test-PortInUse([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

if (Test-PortInUse 8001) {
    Write-Host "== 端口 8001 已被占用（后端可能已在运行），跳过启动后端 ==" -ForegroundColor Yellow
} else {
    Write-Host "== 启动后端 API (main.py, :8001) ==" -ForegroundColor Cyan
    Start-Process -FilePath $py -ArgumentList "main.py" -WorkingDirectory $bk -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

# vector.py 是纯轮询 Worker，不监听端口，需按进程命令行判断是否已在运行
$workerRunning = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*vector.py*" }
if ($workerRunning) {
    Write-Host "== 向量化 Worker (vector.py) 已在运行，跳过 ==" -ForegroundColor Yellow
} else {
    Write-Host "== 启动向量化 Worker (vector.py) ==" -ForegroundColor Cyan
    Start-Process -FilePath $py -ArgumentList "vector.py" -WorkingDirectory $bk -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

if (Test-PortInUse 8080) {
    Write-Host "== 端口 8080 已被占用（前端可能已在运行），跳过启动前端 ==" -ForegroundColor Yellow
} else {
    Write-Host "== 启动前端 (Vite, :8080) ==" -ForegroundColor Cyan
    Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory $ft -WindowStyle Hidden
}

Write-Host ""
Write-Host "已启动完成：" -ForegroundColor Green
Write-Host "  前端页面   http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  后端 API   http://127.0.0.1:8001" -ForegroundColor White
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "  · 首次启动后端需加载模型，约需 10~20 秒才能响应。" -ForegroundColor White
Write-Host "  · 若后端响应慢，可在浏览器等待片刻后刷新前端页面。" -ForegroundColor White
