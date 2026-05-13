@echo off
cd /d "%~dp0"
echo ==========================================
echo   ACTUALIZADOR DE NOTICIAS GASTEIZ
echo ==========================================
echo.

echo [1/4] Scraping noticias nuevas...
python scraper/multi_scraper.py
if %ERRORLEVEL% NEQ 0 goto error

echo [2/4] Reescritura paralela con IA...
python scraper/parallel_rewrite.py
if %ERRORLEVEL% NEQ 0 goto error

echo [3/4] Actualizando Mood de la ciudad...
python scraper/update_mood.py
if %ERRORLEVEL% NEQ 0 goto error

echo [4/4] Actualizando Pipeline de Podcast...
python scraper/update_podcast.py
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
