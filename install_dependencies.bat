@echo off
echo Installing CryBot dependencies...
cd /d "C:\Users\jolab\Desktop\crybot"

echo Installing vk_api...
pip install vk_api==11.9.9

echo Installing python-dotenv...
pip install python-dotenv==1.0.1

echo Installing requests...
pip install requests==2.31.0

echo.
echo Dependencies installed successfully!
echo You can now run start_bot.bat
pause