param(
    [Parameter(Mandatory = $true)][string]$ImagePath,
    [string]$Language = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ImagePath)) {
    throw "Image not found: $ImagePath"
}

$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = (
    [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq "AsTask" -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1"
        } |
        Select-Object -First 1
)
if ($null -eq $asTaskGeneric) {
    throw "Unable to locate WinRT AsTask adapter."
}

function Await-WinRt($Operation, [Type]$ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $task = $asTask.Invoke($null, @($Operation))
    $task.Wait(-1) | Out-Null
    return $task.Result
}

$fullPath = (Resolve-Path -LiteralPath $ImagePath).Path
$file = Await-WinRt (
    [Windows.Storage.StorageFile]::GetFileFromPathAsync($fullPath)
) ([Windows.Storage.StorageFile])
$stream = Await-WinRt (
    $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await-WinRt (
    [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await-WinRt (
    $decoder.GetSoftwareBitmapAsync()
) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = $null
try {
    $ocrLanguage = New-Object Windows.Globalization.Language($Language)
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($ocrLanguage)
} catch {
    $engine = $null
}
if ($null -eq $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if ($null -eq $engine) {
    throw "No OCR engine is available."
}

$result = Await-WinRt (
    $engine.RecognizeAsync($bitmap)
) ([Windows.Media.Ocr.OcrResult])

$lines = @($result.Lines | ForEach-Object { $_.Text })
$text = $lines -join "`n"
$cjk = ([regex]::Matches($text, "[\u3400-\u9FFF]")).Count
$estimatedTokens = if ($text.Length -gt 0) {
    [math]::Ceiling($cjk + (($text.Length - $cjk) / 4.0))
} else {
    0
}

[pscustomobject]@{
    state = "ok"
    image = $fullPath
    language = $engine.RecognizerLanguage.LanguageTag
    lineCount = $lines.Count
    textLength = $text.Length
    estimatedTokens = $estimatedTokens
    text = $text
} | ConvertTo-Json -Depth 4 -Compress
