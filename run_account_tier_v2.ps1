#Requires -Version 7.4
# AccountTierTask v2 — all four systems against the tier-balanced TYS-signal fixture.
# Note: the framework derives the output directory from the task name, so results land in
# results/account_tier/ (live/ + traces/), not results/account_tier_v2/. Run groups are
# timestamped; v2 runs are distinguishable by date and by num_instances=28 in the manifest.
Set-Location "C:\Users\mbusa\repos\continual-learning-bench"

# Load .env
Get-Content .\.env | Where-Object { $_ -match '=' } | ForEach-Object {
    $idx = $_.IndexOf('=')
    Set-Item -Path "Env:$($_.Substring(0, $idx).Trim())" -Value $_.Substring($idx + 1).Trim()
}
$env:PYTHONUTF8 = "1"

Write-Host "=== AccountTierTask v2 — ICL baseline (stateless) ==="
uv run clbench run --config configs/account_tier/account_tier_icl.json --runs 3 --run-mode permute

Write-Host "=== AccountTierTask v2 — ICL-Notepad (memory proxy) ==="
uv run clbench run --config configs/account_tier/account_tier_icl_notepad.json --runs 3 --run-mode permute

Write-Host "=== AccountTierTask v2 — ACE (structured playbook) ==="
uv run clbench run --config configs/account_tier/account_tier_ace.json --runs 3 --run-mode permute

Write-Host "=== AccountTierTask v2 — claude (real Claude Code stack, frozen seed) ==="
uv run clbench run --config configs/account_tier/account_tier_claude.json --runs 3 --run-mode permute

Write-Host "=== Done. Results in results/account_tier/ (v2 run groups by timestamp) ==="
