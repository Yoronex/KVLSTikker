@echo off
title Tikker Server v.1.5.0.2
call git pull
start "" "start_tikker_browser.bat"
call python main.py