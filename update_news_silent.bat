@echo off
cd /d "%~dp0"

:: Versión silenciosa para el Programador de Tareas (sin pausas)
python scraper/multi_scraper.py
python scraper/parallel_rewrite.py
python scraper/update_mood.py
python scraper/update_podcast.py

exit
