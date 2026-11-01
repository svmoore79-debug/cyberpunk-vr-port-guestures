# VRGestures fork: a local build of the patched plugin. The build tree is a second checkout of upstream (no fork commits
# in it): its sources are reset, this branch's vrgestures\ folder is copied in and the patches applied, then built.
#
#     powershell -File vrgestures\build_local.ps1 [-BuildTree ..\cvr-build-020] [-Sdk ..\cvr-build\sdk25] [-Configure]
#
# Two projects at a time: with more, MSVC 14.44 sometimes crashes (CL.exe 0xC0000005) on the larger translation units.
param(
    [string]$BuildTree = "$PSScriptRoot\..\..\cvr-build-020",
    [string]$Sdk = "$PSScriptRoot\..\..\cvr-build\sdk25",
    [switch]$Configure
)
# Not "Stop": Windows PowerShell turns a native tool's stderr (CMake's warnings) into errors. Exit codes are checked.
$ErrorActionPreference = "Continue"
$BuildTree = (Resolve-Path $BuildTree).Path
$Sdk = (Resolve-Path $Sdk).Path
Push-Location $BuildTree
try {
    git checkout -q -- .
    git clean -fdq -e build -e externals -e *.log
    if (Test-Path vrgestures) { Remove-Item vrgestures -Recurse -Force }
    Copy-Item "$PSScriptRoot" vrgestures -Recurse
    python vrgestures\apply_patches.py
    if ($LASTEXITCODE -ne 0) { throw "patches did not apply" }
    if ($Configure -or -not (Test-Path build\CMakeCache.txt)) {
        cmake -S . -B build -G "Visual Studio 17 2022" -A x64 "-DCVR_RED4EXT_SDK_DIR=$($Sdk -replace '\\','/')" *> configure.log
        if ($LASTEXITCODE -ne 0) { Get-Content configure.log -Tail 40; throw "configure failed" }
    }
    cmake --build build --config Release --target cyberpunkvrport_stereo -- /m:2 *> build.log
    $code = $LASTEXITCODE
    Select-String -Path build.log -Pattern ' error |: fatal error|error MSB|LINK : fatal' |
        Select-Object -First 40 | ForEach-Object { $_.Line.Trim() }
    if ($code -ne 0) { throw "build failed ($code)" }
    Get-Item build\bin\red4ext\plugins\cyberpunkvrport\cyberpunkvrport.dll | Select-Object FullName, Length, LastWriteTime
} finally { Pop-Location }
