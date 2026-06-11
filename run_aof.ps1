#Requires -Version 7.4
Set-Location "C:\Users\mbusa\repos\continual-learning-bench"

# Load .env
Get-Content .\.env | Where-Object { $_ -match '=' } | ForEach-Object {
    $idx = $_.IndexOf('=')
    Set-Item -Path "Env:$($_.Substring(0, $idx).Trim())" -Value $_.Substring($idx + 1).Trim()
}

Write-Host "=== AOFViolationsTask — ICL baseline (stateless) ==="
uv run clbench run --config configs/aof_violations/aof_violations_icl.json --runs 3 --run-mode permute

Write-Host "=== AOFViolationsTask — ICL-Notepad (memory proxy) ==="
uv run clbench run --config configs/aof_violations/aof_violations_icl_notepad.json --runs 3 --run-mode permute

Write-Host "=== AOFViolationsTask — ACE (structured playbook) ==="
uv run clbench run --config configs/aof_violations/aof_violations_ace.json --runs 3 --run-mode permute

Write-Host "=== Done. Results in results/aof_violations/ ==="
