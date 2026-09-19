# List matching items in the Windows Recycle Bin (verification helper).
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File list-bin.ps1 -Name "*pattern*"
# Prints:  FOUND: <name> | orig=<original folder> | deleted=<timestamp>
param([string]$Name = "*")
$ErrorActionPreference = "Stop"
$sh = New-Object -ComObject Shell.Application
$bin = $sh.Namespace(10)
$items = $bin.Items()
$count = 0
foreach ($i in $items) {
    if ($i.Name -like $Name) {
        $orig = $bin.GetDetailsOf($i, 1)
        $del = $bin.GetDetailsOf($i, 2)
        Write-Output ("FOUND: {0} | orig={1} | deleted={2}" -f $i.Name, $orig, $del)
        $count++
    }
}
Write-Output ("MATCH_COUNT=$count TOTAL_ITEMS=" + $items.Count)
