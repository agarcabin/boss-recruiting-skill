param(
    [string]$TargetRoot = (Join-Path $env:USERPROFILE '.codex\skills\boss-recruiting'),
    [string]$CacheRoot = (Join-Path $env:LOCALAPPDATA 'Codex\recruiting-greetings\runtime-cache'),
    [string]$LockFile,
    [string]$AssetDirectory,
    [string]$Archive,
    [string]$Signature,
    [switch]$SkipUnlock
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Obtain this script independently from the official repository HTTPS page.
# Only this fixed digest and key authorize executable downloads, including mirrors.
$LockSha256 = 'f85098aa0fb7b69e3be7b1374a9576cc25d68f9e8a2dc20e7d6ffa55581e70da'
$PublisherKey = 'AI9bAlI7fNGkfQM80R52e9h10iHXeZbJNhHcI0DECBE='
$Repository = 'agarcabin/boss-recruiting-skill'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$TargetRoot = [IO.Path]::GetFullPath($TargetRoot)
$CacheRoot = [IO.Path]::GetFullPath($CacheRoot)
New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
function Test-Digest([string]$Path,[string]$Expected) {
    return (Test-Path -LiteralPath $Path -PathType Leaf) -and ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected.ToLowerInvariant())
}
function Receive-File([string]$Url,[string]$Path,[string]$Expected = '') {
    if ($Expected -and (Test-Digest $Path $Expected)) { return }
    $routes = @($Url)
    if ($Url.StartsWith('https://github.com/') -or $Url.StartsWith('https://raw.githubusercontent.com/')) {
        $routes += @('https://gh-proxy.org/' + $Url, 'https://ghfast.top/' + $Url)
    }
    $part = $Path + '.part'
    foreach ($route in $routes) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $route -OutFile $part -TimeoutSec 120
            if ($Expected -and -not (Test-Digest $part $Expected)) { throw 'download_digest_mismatch' }
            Move-Item -LiteralPath $part -Destination $Path -Force
            return
        } catch { Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue }
    }
    throw ('download_failed: ' + $Url)
}
if (-not $LockFile) {
    $adjacent = Join-Path $PSScriptRoot '..\references\runtime-lock.json'
    if (Test-Digest $adjacent $LockSha256) { $LockFile = $adjacent }
    else {
        $LockFile = Join-Path $CacheRoot 'runtime-lock.json'
        Receive-File ('https://raw.githubusercontent.com/' + $Repository + '/main/references/runtime-lock.json') $LockFile $LockSha256
    }
}
if (-not (Test-Digest $LockFile $LockSha256)) { throw 'untrusted_dependency_lock' }
$lock = Get-Content -LiteralPath $LockFile -Raw | ConvertFrom-Json
if ($lock.schema -ne 'boss-runtime-lock/v1' -or $lock.platform -ne 'windows-x64') { throw 'invalid_runtime_lock' }
$downloads = Join-Path $CacheRoot 'downloads'
New-Item -ItemType Directory -Path $downloads -Force | Out-Null
function Obtain-Asset($item) {
    $dest = Join-Path $downloads $item.filename
    if ($AssetDirectory) {
        $local = Join-Path $AssetDirectory $item.filename
        if (Test-Path -LiteralPath $local -PathType Leaf) {
            if (-not (Test-Digest $local $item.sha256)) { throw 'offline_asset_digest_mismatch' }
            if (-not (Test-Digest $dest $item.sha256)) { Copy-Item -LiteralPath $local -Destination $dest -Force }
        }
    }
    Receive-File $item.url $dest $item.sha256
    return $dest
}
$runtimeArchive = Obtain-Asset $lock.python
$runtimeHome = Join-Path $CacheRoot ('python-' + $LockSha256.Substring(0,16))
$python = Join-Path $runtimeHome 'python\python.exe'
$marker = Join-Path $runtimeHome 'verified-lock.sha256'
if (-not ((Test-Path -LiteralPath $python) -and (Test-Path -LiteralPath $marker) -and ((Get-Content -LiteralPath $marker -Raw).Trim() -eq $LockSha256))) {
    if (Test-Path -LiteralPath $runtimeHome) {
        $resolved = [IO.Path]::GetFullPath($runtimeHome)
        if (-not $resolved.StartsWith($CacheRoot.TrimEnd('\') + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'unsafe_runtime_cache' }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    New-Item -ItemType Directory -Path $runtimeHome -Force | Out-Null
    & tar.exe -xzf $runtimeArchive -C $runtimeHome
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python)) { throw 'runtime_extraction_failed' }
    $requirements = @()
    foreach ($wheel in $lock.wheels) {
        $null = Obtain-Asset $wheel
        $requirements += ($wheel.name + '==' + $wheel.version + ' --hash=sha256:' + $wheel.sha256)
    }
    $requirementsFile = Join-Path $runtimeHome 'requirements-lock.txt'
    [IO.File]::WriteAllLines($requirementsFile,$requirements,[Text.Encoding]::ASCII)
    & $python -I -m pip install --disable-pip-version-check --no-index --find-links $downloads --require-hashes -r $requirementsFile
    if ($LASTEXITCODE -ne 0) { throw 'runtime_dependency_install_failed' }
    & $python -I -c "import ssl,tkinter,cryptography,openpyxl,pypdf,rapidocr,onnxruntime,cv2,numpy; import pathlib,rapidocr; p=pathlib.Path(rapidocr.__file__).parent/'models'; assert len(list(p.glob('*.onnx')))>=3; print('runtime_ready')"
    if ($LASTEXITCODE -ne 0) { throw 'runtime_probe_failed' }
    [IO.File]::WriteAllText($marker,$LockSha256,[Text.Encoding]::ASCII)
}
if (-not $Archive) {
    $release = Invoke-RestMethod -Uri ('https://api.github.com/repos/' + $Repository + '/releases/latest') -Headers @{ 'User-Agent'='boss-skill-bootstrap' }
    $asset = @($release.assets | Where-Object { $_.name -match '^boss-recruiting-[0-9.]+\.zip$' })
    if ($asset.Count -ne 1) { throw 'release_archive_missing' }
    $sigAsset = @($release.assets | Where-Object { $_.name -eq ($asset[0].name + '.sig') })
    if ($sigAsset.Count -ne 1) { throw 'release_signature_missing' }
    $Archive = Join-Path $downloads $asset[0].name
    $Signature = $Archive + '.sig'
    Receive-File $asset[0].browser_download_url $Archive
    Receive-File $sigAsset[0].browser_download_url $Signature
}
if (-not $Signature) { throw 'signature_required' }
$stage = Join-Path $CacheRoot ('release-' + [Guid]::NewGuid().ToString('N'))
$verify = @'
import base64,hashlib,json,pathlib,re,sys,zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
archive,signature,public,destination=sys.argv[1:]
data=pathlib.Path(archive).read_bytes()
if len(data)>32*1024*1024:raise ValueError('archive_too_large')
signature=json.loads(pathlib.Path(signature).read_text(encoding='utf-8-sig'))
assert signature['algorithm']=='Ed25519'
Ed25519PublicKey.from_public_bytes(base64.b64decode(public,validate=True)).verify(base64.b64decode(signature['signature'],validate=True),data)
root=pathlib.Path(destination);root.mkdir()
with zipfile.ZipFile(archive) as z:
    names=set();total=0
    for item in z.infolist():
        p=pathlib.PurePosixPath(item.filename)
        if p.is_absolute() or not p.parts or any(x in ('','..','.') or x.rstrip(' .')!=x for x in p.parts) or ':' in item.filename or '\\' in item.filename:raise ValueError('unsafe_archive_path')
        if item.filename in names or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('unsafe_archive_entry')
        names.add(item.filename);total+=item.file_size
        if item.file_size>16*1024*1024 or total>64*1024*1024:raise ValueError('archive_expansion_limit')
        if not item.is_dir():
            path=root/item.filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(item))
print('release_signature_verified')
'@
$verify | & $python -I - $Archive $Signature $PublisherKey $stage
if ($LASTEXITCODE -ne 0) { throw 'release_verification_failed' }
& $python -E -s (Join-Path $stage 'scripts\skill_update.py') install-local --root $TargetRoot --archive $Archive --signature $Signature --runtime-source (Join-Path $runtimeHome 'python')
if ($LASTEXITCODE -ne 0) { throw 'installation_failed_see_recovery_journal' }
& $python -E -s (Join-Path $TargetRoot 'scripts\project_vault.py') status
if ($LASTEXITCODE -ne 0) { throw 'project_status_failed' }
# Fresh installs unlock only after selecting the encrypted group in the project list.
Write-Output 'installation_complete'
