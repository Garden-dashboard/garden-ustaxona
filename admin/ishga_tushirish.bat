@echo off
start http://localhost:5056/
cd /d "%~dp0"
python server.py
