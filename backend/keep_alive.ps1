$baseUrl = "https://livenews-ai-backend.onrender.com"
$duration = 15
$interval = 240

$endTime = (Get-Date).AddMinutes($duration)
Write-Host "Keep-alive started for $duration minutes, pinging every $interval seconds"

while ((Get-Date) -lt $endTime) {
    try {
        $response = Invoke-RestMethod -Method GET -Uri "$baseUrl/api/categories" -TimeoutSec 10
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Ping OK - Service alive"
    } catch {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Ping FAILED - $($_.Exception.Message)"
    }
    Start-Sleep -Seconds $interval
}

Write-Host "Keep-alive finished"
