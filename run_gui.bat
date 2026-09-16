@echo off
title Benchmark Cryptography GUI Launcher
cd /d "%~dp0"
echo ============================================================
echo   KHOI DONG GIAO DIEN BENCHMARK MA HOA MANG
echo ============================================================
echo.
python benchmark_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo [!] Khong the khoi dong Benchmark GUI!
    echo     Hay thu chay: python -m pip install -r requirements.txt
    echo ============================================================
    echo.
    pause
)
