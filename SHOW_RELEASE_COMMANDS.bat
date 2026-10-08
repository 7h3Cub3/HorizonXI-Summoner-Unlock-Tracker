@echo off
echo 1. git add .
echo 2. git commit -m "Release v24.0.0"
echo 3. git push origin main
echo 4. git tag -a v24.0.0 -m "Future forecast range selector"
echo 5. git push origin v24.0.0
echo 6. gh run watch
echo 7. gh release view v24.0.0 --web
