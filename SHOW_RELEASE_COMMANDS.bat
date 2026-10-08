@echo off
echo 1. git add .
echo 2. git commit -m "Release v22.0.0"
echo 3. git push origin main
echo 4. git tag -a v22.0.0 -m "UTC weather timestamp fix"
echo 5. git push origin v22.0.0
echo 6. gh run watch
echo 7. gh release view v22.0.0 --web
