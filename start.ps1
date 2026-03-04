Write-Host "Starting Backend Server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\testcode\audata; python main.py"

Start-Sleep -Seconds 5

Write-Host "Starting Frontend Server..." -ForegroundColor Green  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\testcode\audata\frontend; npm start"

Write-Host ""
Write-Host "Services are starting..." -ForegroundColor Yellow
Write-Host "Backend API: http://localhost:8002" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
