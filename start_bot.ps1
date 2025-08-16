# PowerShell script to start CryBot
Set-Location "C:\Users\jolab\Desktop\crybot"
Write-Host "Starting CryBot..." -ForegroundColor Green

try {
    python bot_vk.py
}
catch {
    Write-Host "Error starting bot: $_" -ForegroundColor Red
    Read-Host "Press Enter to continue"
}