@echo off
set CONFLUENCE_EMAIL=opp191@neowiz.com
set CONFLUENCE_TOKEN=ATATT3xFfGF0eqJZKV9sKqZ41TtEKcJZ4-9FFj4_kDioZo-S0gfxPWxF9mvVhbYZKAtzhsB9wND-PDTJXxGd02JhTEq2tlTCiLIvCt0W-tYDr8kIa29rKrx2ev49KiDiuBz5DBo3dqwf88d9z-woItnE5i0tD3VfAcpW8s1jLMnWVo-4gHejHKE=09286A3D
set INDEX_PATH=C:\Users\opp191\Documents\AIConfluenceArchiving-auto\index.html

python C:\Users\opp191\Documents\AIConfluenceArchiving-auto\update_pages_v7.py

cd C:\Users\opp191\Documents\AIConfluenceArchiving-auto
git add index.html
git commit -m "자동 업데이트 %date%"
git push

echo 완료!
