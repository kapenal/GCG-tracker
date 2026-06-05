# 매일 가격 수집 (Docker API 가동 중일 때)
$ErrorActionPreference = 'Stop'
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/sync' | ConvertTo-Json -Depth 5
