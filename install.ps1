[CmdletBinding()]
param(
    [string]$Destination = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\skills\certificate-template-studio'),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$sourceRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$destinationRoot = [System.IO.Path]::GetFullPath($Destination)

if ([System.IO.Path]::GetFileName($destinationRoot) -ne 'certificate-template-studio') {
    throw '安装目标目录名必须是 certificate-template-studio。'
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw '找不到 Python。请先安装 Python 3.10 或更高版本。'
}

& $pythonCommand.Source (Join-Path $sourceRoot 'scripts\quick_validate.py') $sourceRoot
if ($LASTEXITCODE -ne 0) {
    throw '源 Skill 校验失败，安装已停止。'
}

if ($sourceRoot -eq $destinationRoot) {
    Write-Output "Skill 已位于目标目录并通过校验：$destinationRoot"
    exit 0
}

$backupRoot = $null
if (Test-Path -LiteralPath $destinationRoot) {
    $hasFiles = @(Get-ChildItem -LiteralPath $destinationRoot -Force).Count -gt 0
    if ($hasFiles -and -not $Force) {
        throw '目标目录非空。请使用 -Force 创建备份后更新，或指定其他目录。'
    }
    if ($hasFiles) {
        $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backupRoot = "$destinationRoot.backup-$timestamp"
        if (Test-Path -LiteralPath $backupRoot) {
            throw "备份目标已存在：$backupRoot"
        }
        Move-Item -LiteralPath $destinationRoot -Destination $backupRoot
    }
}

[System.IO.Directory]::CreateDirectory($destinationRoot) | Out-Null

$topFiles = @(
    'SKILL.md', 'README.md', 'README.en.md', 'LICENSE',
    'LICENSE-ASSETS.md', 'NOTICE.md', 'requirements-dev.txt'
)
$runtimeDirectories = @('agents', 'assets', 'examples', 'prompts', 'references', 'schemas', 'scripts')

foreach ($file in $topFiles) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $file) -Destination (Join-Path $destinationRoot $file)
}
foreach ($directory in $runtimeDirectories) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $directory) -Destination (Join-Path $destinationRoot $directory) -Recurse
}

& $pythonCommand.Source (Join-Path $destinationRoot 'scripts\quick_validate.py') $destinationRoot
if ($LASTEXITCODE -ne 0) {
    throw "安装后的 Skill 校验失败。旧版本备份仍保留在：$backupRoot"
}

Write-Output "安装完成：$destinationRoot"
if ($backupRoot) {
    Write-Output "旧版本备份：$backupRoot"
}
