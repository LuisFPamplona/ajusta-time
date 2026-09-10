[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Este script deve ser executado no Windows."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$specPath = Join-Path $projectRoot "AjustaTime.spec"
$buildPath = Join-Path $projectRoot "build"
$distPath = Join-Path $projectRoot "dist"
$bundlePath = Join-Path $distPath "Ajusta Time"
$executablePath = Join-Path $bundlePath "Ajusta Time.exe"

if (-not (Test-Path -LiteralPath $specPath -PathType Leaf)) {
    throw "Arquivo de configuração não encontrado: $specPath"
}

Get-Command python -ErrorAction Stop | Out-Null

& python --version
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível executar o Python."
}

& python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller não está instalado no ambiente ativo."
}

foreach ($generatedPath in @($buildPath, $distPath)) {
    if (Test-Path -LiteralPath $generatedPath) {
        Remove-Item -LiteralPath $generatedPath -Recurse -Force
    }
}

Push-Location $projectRoot
try {
    & python -m PyInstaller --noconfirm --clean $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "O PyInstaller encerrou com código $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
    throw "Executável não encontrado: $executablePath"
}

$executable = Get-Item -LiteralPath $executablePath
if ($executable.Length -le 0) {
    throw "O executável gerado está vazio."
}

$bundleFiles = @(Get-ChildItem -LiteralPath $bundlePath -Recurse -File)
if ($bundleFiles.Count -le 1) {
    throw "A pasta ONEDIR não contém as dependências esperadas."
}

foreach ($requiredFile in @("qwindows.dll", "Qt6PrintSupport.dll", "_sqlite3.pyd")) {
    if (-not ($bundleFiles | Where-Object Name -EQ $requiredFile)) {
        throw "Dependência obrigatória não encontrada no bundle: $requiredFile"
    }
}

Write-Host "Build Windows concluído: $executablePath"
Write-Host "Arquivos no bundle ONEDIR: $($bundleFiles.Count)"
