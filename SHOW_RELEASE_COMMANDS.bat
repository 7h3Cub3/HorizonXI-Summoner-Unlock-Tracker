@echo off
echo Example manual release sequence:
echo.
echo   build_exe.bat
echo   git add .
echo   git commit -m "Release v15.0.0"
echo   git push
echo   git tag v15.0.0
echo   git push origin v15.0.0
echo   gh release create v15.0.0 "dist\HorizonXI_Summoner_Unlock_Tracker.exe" --title "v15.0.0" --generate-notes
