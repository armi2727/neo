@echo off
cd /d C:\Users\opp191\Documents\AIConfluenceArchiving-auto
set CONFLUENCE_EMAIL=opp191@neowiz.com
set CONFLUENCE_TOKEN=ATATT3xFfGF02IP7wHba7pACkoX9EZEF99O94S2Oxaa3wHlXeihJAiJdMGcUUjui0jPhYtmR3BkJttxInCJx8Udzjd5dxN4vBhtSwmyuNm1BgBgOvjVFmVM0pTHmFucRN1YfQh5IS0LQKN6YlNZegonFrPKFR_Muj7eFDuFbRfLJo_KKVdTgnAU=693C5658
set INDEX_PATH=C:\Users\opp191\Documents\AIConfluenceArchiving-auto\index.html
set PYTHONIOENCODING=utf-8
set PYTHONHTTPSVERIFY=0
set REQUESTS_CA_BUNDLE=
python update_pages_v10.py >> update_log.txt 2>&1
git add index.html
git commit -m "update %date%"
git push
echo done!
