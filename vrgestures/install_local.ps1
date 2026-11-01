# VRGestures fork: install port 0.2.0 with the fork's build over it, with the game CLOSED.
#
#     powershell -File vrgestures\install_local.ps1 -Zip <CyberpunkVRPort-0.2.0.zip> [-Game <game root>] [-BuildTree ..\cvr-build-020]
#
# 1. The 0.1.9 pieces 0.2.0 does not take out by itself are moved to _vrg_stage\port-0.1.9-backup (the old plugin folder
#    red4ext\plugins\CyberpunkVR_Stereo, engine\config\platform\pc\vrcam_cpu_tweaks.ini), and CET's CyberpunkVRPort_*
#    folders are copied there too (the plugin moves them itself at its first start, settings included).
# 2. The release zip is unpacked over the game.
# 3. The fork's files go over it: the plugin DLL, and the port Lua mods and scripts the patches change.
#    -Artifact <folder>: the unzipped GitHub build artifact (CyberpunkVRPort-0.2.0-vrgestures) instead of a local build.
param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [string]$Game = "D:\SteamLibrary\steamapps\common\Cyberpunk 2077",
    [string]$BuildTree = "$PSScriptRoot\..\..\cvr-build-020",
    [string]$Artifact = ""
)
$ErrorActionPreference = "Stop"
if (Get-Process Cyberpunk2077 -ErrorAction SilentlyContinue) { throw "Close the game first." }
if ($Artifact) {
    $Artifact = (Resolve-Path $Artifact).Path
    if (-not (Test-Path (Join-Path $Artifact "red4ext\plugins\cyberpunkvrport\cyberpunkvrport.dll"))) { throw "No cyberpunkvrport.dll in $Artifact" }
} else {
    $BuildTree = (Resolve-Path $BuildTree).Path
    $dll = Join-Path $BuildTree "build\bin\red4ext\plugins\cyberpunkvrport\cyberpunkvrport.dll"
    if (-not (Test-Path $dll)) { throw "No fork build at $dll -- run build_local.ps1 first." }
}

$backup = Join-Path $Game "_vrg_stage\port-0.1.9-backup"
New-Item -ItemType Directory -Force $backup | Out-Null
$old = Join-Path $Game "red4ext\plugins\CyberpunkVR_Stereo"
if (Test-Path $old) { Move-Item $old (Join-Path $backup "CyberpunkVR_Stereo") -Force; "moved the 0.1.9 plugin folder to the backup" }
$ini = Join-Path $Game "engine\config\platform\pc\vrcam_cpu_tweaks.ini"
if (Test-Path $ini) { Move-Item $ini $backup -Force; "moved vrcam_cpu_tweaks.ini to the backup" }
$cet = Join-Path $Game "bin\x64\plugins\cyber_engine_tweaks\mods"
Get-ChildItem $cet -Directory -Filter "CyberpunkVRPort_*" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $backup "cet\$($_.Name)") -Recurse -Force
}
Copy-Item (Join-Path $Game "bin\x64\vrport.ini") $backup -Force -ErrorAction SilentlyContinue

# the zip, file by file (paths under the game root only)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead((Resolve-Path $Zip).Path)
$root = [IO.Path]::GetFullPath($Game).TrimEnd('\') + '\'
$n = 0
try {
    foreach ($e in $archive.Entries) {
        if ($e.FullName.EndsWith('/') -or $e.FullName.EndsWith('\')) { continue }
        $rel = $e.FullName -replace '/', '\'
        if ($rel -match '^(CHANGELOG|INSTALL|UNINSTALL)\.') { continue }
        $dest = [IO.Path]::GetFullPath((Join-Path $Game $rel))
        if (-not $dest.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw "zip entry outside the game: $rel" }
        New-Item -ItemType Directory -Force (Split-Path $dest -Parent) | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($e, $dest, $true)
        $n++
    }
} finally { $archive.Dispose() }
"unpacked $n files from the release zip"

# the fork's files
$plug = Join-Path $Game "red4ext\plugins\cyberpunkvrport"
if ($Artifact) {
    Copy-Item (Join-Path $Artifact "red4ext") $Game -Recurse -Force
    "installed the fork's build from $Artifact"
    Get-Item (Join-Path $plug "cyberpunkvrport.dll") | Select-Object FullName, Length, LastWriteTime
    return
}
Copy-Item $dll $plug -Force
$pdb = [IO.Path]::ChangeExtension($dll, ".pdb")
if (Test-Path $pdb) { Copy-Item $pdb $plug -Force }
$lua = @(
    "CyberpunkVRPort_Menu\modules\menu.lua",
    "CyberpunkVRPort_Menu\modules\quickwheel.lua",
    "CyberpunkVRPort_Weapon\init.lua",
    "CyberpunkVRPort_WristHud\init.lua"
)
foreach ($f in $lua) {
    $dst = Join-Path $plug "lua\$f"
    New-Item -ItemType Directory -Force (Split-Path $dst -Parent) | Out-Null
    Copy-Item (Join-Path $BuildTree "mods\cet\$f") $dst -Force
}
foreach ($f in @("vrport_cyberware.reds", "vrport_launcher_aim.reds", "vrport_launcher_selection.reds")) {
    Copy-Item (Join-Path $BuildTree "mods\redscript\CyberpunkVRPort_Cyberware\$f") (Join-Path $plug "scripts\CyberpunkVRPort_Cyberware\$f") -Force
}
"installed the fork's plugin, $($lua.Count) Lua files and 3 scripts"
Get-Item (Join-Path $plug "cyberpunkvrport.dll") | Select-Object FullName, Length, LastWriteTime
