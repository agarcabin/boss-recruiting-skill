param(
    [string]$OutputPath = (Join-Path $PSScriptRoot 'release\打开招呼配置.exe')
)

$ErrorActionPreference = 'Stop'
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$source = Join-Path $PSScriptRoot 'src\招呼配置服务.cs'
$html = Join-Path $PSScriptRoot 'src\招呼配置.html'

if (-not (Test-Path -LiteralPath $compiler)) {
    throw '未找到 Windows 自带的 .NET Framework 编译器。'
}
if (Select-String -LiteralPath $source, $html -Pattern 'sk-[A-Za-z0-9]{20,}' -Quiet) {
    throw '源码中检测到疑似 API Key，已停止构建。'
}

$resolvedOutput = [IO.Path]::GetFullPath($OutputPath)
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'release'))
if (-not $resolvedOutput.StartsWith($releaseRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw '输出文件必须位于 release 目录。'
}
New-Item -ItemType Directory -Path (Split-Path $resolvedOutput) -Force | Out-Null

& $compiler `
    /nologo `
    /target:winexe `
    /platform:anycpu `
    /optimize+ `
    /codepage:65001 `
    /reference:System.Web.Extensions.dll `
    /reference:System.Windows.Forms.dll `
    /reference:System.Security.dll `
    "/resource:$html,GreetingConfig.Html" `
    "/out:$resolvedOutput" `
    $source

if ($LASTEXITCODE -ne 0) {
    throw "编译失败，退出码：$LASTEXITCODE"
}

Get-Item -LiteralPath $resolvedOutput |
    Select-Object FullName, Length, LastWriteTime
