$ErrorActionPreference = "Stop"
$root = "C:\Users\User\GardenUstaxona"
$log = Join-Path $root "hourly_sync.log"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $log -Value "$ts  $msg"
}

Write-Log "=== Boshlandi ==="

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$syncOutput = & python "$root\scripts\sync_iiko.py" 2>&1
$syncExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap

$syncOutput | ForEach-Object { Write-Log "  [sync] $_" }

if ($syncExit -ne 0) {
    Write-Log "XATO: sync_iiko.py muvaffaqiyatsiz tugadi (kod $syncExit), nashr qilinmadi."
    exit 1
}

Set-Location $root
$changed = git status --porcelain
if ($changed) {
    git add -A | Out-Null
    git commit -m "Avtomatik sinxronlash: iikodagi o'zgarishlar" | Out-Null
    git push | Out-Null
    Write-Log "OK: o'zgarishlar GitHub'ga yuborildi."
} else {
    Write-Log "OK: o'zgarish yo'q."
}
