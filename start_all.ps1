# ResearchX 一键启动脚本（Windows PowerShell）
# 用法：右键"使用 PowerShell 运行"，或在 PowerShell 中执行  .\start_all.ps1
# 说明：基于脚本自身所在目录定位前后端，压缩解压到任意路径均可启动。
$ErrorActionPreference = "Stop"

# ---- 路径定位（相对脚本目录，不写死盘符）----
$root = $PSScriptRoot
$bk   = Join-Path $root "ResearchX_Backend"
$ft   = Join-Path $root "ResearchX_Frontend"
$py   = Join-Path $bk ".venv\Scripts\python.exe"

# ---- 前置自检 ----
$missing = @()

if (-not (Test-Path -LiteralPath $py)) {
    $missing += "后端 Python 环境 .venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath (Join-Path $bk ".env"))) {
    $missing += "后端配置 ResearchX_Backend\.env（可从 .env.example 复制并填入 API Key）"
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
    $missing += "前端依赖 node_modules（请先在 ResearchX_Frontend 目录执行 npm install）"
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
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync('127.0.0.1', $Port)
        return $connection.Wait(1500) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

if (Test-PortInUse 8001) {
    try {
        $apiInfo = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/openapi.json' -TimeoutSec 8
        if ($apiInfo.info.title -ne 'ResearchX API') {
            throw "8001 当前运行的是 $($apiInfo.info.title)，请关闭占用端口的旧后端后重试。"
        }
        Write-Host "== ResearchX 后端已在 8001 运行，跳过启动 ==" -ForegroundColor Yellow
    } catch {
        Write-Host "== 后端端口冲突：$($_.Exception.Message) ==" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "== 启动后端 API (main.py, :8001) ==" -ForegroundColor Cyan
    Start-Process -FilePath $py -ArgumentList "main.py" -WorkingDirectory $bk -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

# vector.py 不监听端口。仅识别本项目的进程；无法读取进程列表时避免重复启动。
try {
    $workerProcesses = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction Stop
    $workerRunning = $workerProcesses | Where-Object { $_.CommandLine -like "*$bk*vector.py*" }
    if ($workerRunning) {
        Write-Host "== ResearchX 向量化 Worker 已在运行，跳过 ==" -ForegroundColor Yellow
    } else {
        Write-Host "== 启动向量化 Worker (vector.py) ==" -ForegroundColor Cyan
        Start-Process -FilePath $py -ArgumentList "vector.py" -WorkingDirectory $bk -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "== 无法核对 Worker 进程，已跳过自动启动以避免重复运行 ==" -ForegroundColor Yellow
}

if (Test-PortInUse 8080) {
    try {
        $currentPage = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/login' -TimeoutSec 5
        if ($currentPage.Content -notmatch '<title>ResearchX') {
            throw '8080 正在运行其他项目，当前不是 ResearchX 前端。请先关闭占用端口的旧服务。'
        }
        Write-Host "== ResearchX 前端已在 8080 运行，跳过启动 ==" -ForegroundColor Yellow
    } catch {
        Write-Host "== 前端端口冲突：$($_.Exception.Message) ==" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "== 启动前端 (Vite, :8080) ==" -ForegroundColor Cyan
    Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory $ft -WindowStyle Hidden
    $ready = $false
    # 首次启动 Vite 需要预构建大量组件，给它足够时间完成编译。
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $page = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/login' -TimeoutSec 2
            if ($page.Content -match '<title>ResearchX') { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) {
        Write-Host '== ResearchX 前端未在 8080 成功启动，请检查端口占用或 Vite 日志 ==' -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "已启动完成：" -ForegroundColor Green
Write-Host "  前端页面   http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  后端 API   http://127.0.0.1:8001" -ForegroundColor White
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "  · 首次启动后端需加载模型，约需 10~20 秒才能响应。" -ForegroundColor White
Write-Host "  · 若后端响应慢，可在浏览器等待片刻后刷新前端页面。" -ForegroundColor White
