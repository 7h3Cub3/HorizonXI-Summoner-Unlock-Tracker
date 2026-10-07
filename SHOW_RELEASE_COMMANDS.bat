@echo off
echo Example manual release sequence:
echo.
echo   build_exe.bat
echo   git add .
echo   git commit -m "Release v18.0.0"
echo   git push
echo   git tag v18.0.0
echo   git push origin v18.0.0
echo   gh release create v18.0.0 "dist\HorizonXI_Summoner_Unlock_Tracker.exe" --title "v18.0.0" --generate-notes
