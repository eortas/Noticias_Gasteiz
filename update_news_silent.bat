@echo off
if not "%minimized%"=="" goto :minimized
set minimized=true
start /min "" "%~dpnx0"
exit

:minimized
cd /d "%~dp0"

:: Versión silenciosa para el Programador de Tareas (sin pausas)
python scraper/multi_scraper.py
python scraper/parallel_rewrite.py
python scraper/update_mood.py
python scraper/update_podcast.py

git add .
git commit -m "Auto-update noticias: %date% %time%"
git push

exit
