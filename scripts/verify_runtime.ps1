param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$skillRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runtimeRoot = Join-Path $skillRoot "runtime\win-x64"
$python = Join-Path $runtimeRoot "python\python.exe"
$models = Join-Path $runtimeRoot "python\Lib\site-packages\rapidocr\models"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Bundled Python is missing: $python"
}
foreach ($model in @(
    "PP-OCRv6_det_small.onnx",
    "PP-OCRv6_rec_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx"
)) {
    $path = Join-Path $models $model
    if (-not (Test-Path -LiteralPath $path)) {
        throw "RapidOCR model is missing: $path"
    }
}

$probe = @'
import importlib.metadata
import json
import sys

import cv2
import numpy
import onnxruntime
import openpyxl
import pypdf
import rapidocr

print(json.dumps({
    "state": "ok",
    "python": sys.version.split()[0],
    "rapidocr": importlib.metadata.version("rapidocr"),
    "onnxruntime": onnxruntime.__version__,
    "opencv": cv2.__version__,
    "numpy": numpy.__version__,
    "openpyxl": openpyxl.__version__,
    "pypdf": pypdf.__version__,
}, ensure_ascii=False))
'@

$probeOutput = $probe | & $python -
if ($LASTEXITCODE -ne 0) {
    throw "Bundled Python dependency probe failed."
}
$result = $probeOutput | ConvertFrom-Json
$modelDetails = foreach ($model in @(
    "PP-OCRv6_det_small.onnx",
    "PP-OCRv6_rec_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx"
)) {
    $path = Join-Path $models $model
    [ordered]@{
        name = $model
        bytes = (Get-Item -LiteralPath $path).Length
    }
}
$payload = [ordered]@{
    state = "ok"
    skillRoot = $skillRoot
    runtimeRoot = $runtimeRoot
    python = $python
    versions = $result
    models = @($modelDetails)
}

if ($Json) {
    $payload | ConvertTo-Json -Depth 6
}
else {
    [pscustomobject]@{
        State = "ok"
        Python = $result.python
        RapidOCR = $result.rapidocr
        ONNXRuntime = $result.onnxruntime
        OpenCV = $result.opencv
        Models = @($modelDetails).Count
        Runtime = $runtimeRoot
    } | Format-List
}
