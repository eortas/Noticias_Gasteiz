@echo off
cd /d "%~dp0"
echo ==========================================
echo   ACTUALIZADOR DE NOTICIAS GASTEIZ
echo ==========================================
echo.

echo [1/8] Scraping noticias nuevas...
python scraper/multi_scraper.py
if %ERRORLEVEL% NEQ 0 goto error

echo [2/8] Filtrando publirreportajes encubiertos con IA...
python scraper/filter_sponsored.py
if %ERRORLEVEL% NEQ 0 goto error

echo [3/8] Reescritura paralela con IA...
python scraper/parallel_rewrite.py
if %ERRORLEVEL% NEQ 0 goto error

echo [4/8] Agrupando noticias y validando con IA...
python scraper/group_news.py
if %ERRORLEVEL% NEQ 0 goto error

echo [5/8] Actualizando Mood de la ciudad...
python scraper/update_mood.py
if %ERRORLEVEL% NEQ 0 goto error

echo [6/8] Actualizando Pipeline de Podcast...
python scraper/update_podcast.py
if %ERRORLEVEL% NEQ 0 goto error

echo [7/8] Enviando noticias a Telegram...
python scraper/enviar_telegram.py
if %ERRORLEVEL% NEQ 0 goto error

echo [8/8] Subiendo cambios a GitHub...
git add .
git commit -m "Auto-update noticias: %date% %time%"
git push
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo ==========================================
echo   ACTUALIZACION COMPLETADA CON EXITO
echo ==========================================
pause
exit

:error
echo.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo   ERROR DETECTADO EN EL PROCESO
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
pause
exit
