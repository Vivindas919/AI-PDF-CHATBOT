@echo off
title Push to GitHub
cd /d "%~dp0"
echo ========================================================
echo       Pushing AI-PDF-CHATBOT to GitHub (Vivindas919)
echo ========================================================
echo.
echo If prompted, please sign in with your GitHub account: Vivindas919
echo.
git push -u origin main
echo.
pause
