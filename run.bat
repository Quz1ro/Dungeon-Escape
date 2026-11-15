@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"
if errorlevel 1 (
    echo Не вдалося відкрити папку гри.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" goto install

py -3.12 -c "import sys" >nul 2>&1
if errorlevel 1 goto find_python
py -3.12 -m venv ".venv"
if errorlevel 1 goto error
goto install

:find_python
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto try_python
py -3 -m venv ".venv"
if errorlevel 1 goto error
goto install

:try_python
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 (
    echo Не знайдено Python 3.10 або новішого.
    echo Установіть Python 3.12 з python.org і повторіть запуск.
    goto error
)
python -m venv ".venv"
if errorlevel 1 goto error

:install
".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 (
    echo Середовище .venv недоступне або містить застарілий Python.
    goto error
)
echo Підготовка залежностей...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --only-binary=:all: -r "requirements.txt"
if errorlevel 1 (
    echo Не вдалося встановити Pygame. Перевірте підключення до інтернету.
    echo Рекомендована версія Python для гри — 3.12.
    goto error
)

echo Запуск Dungeon Escape...
".venv\Scripts\python.exe" "main.py"
if errorlevel 1 goto error
popd
exit /b 0

:error
echo Не вдалося запустити гру. Подробиці наведено вище.
popd
pause
exit /b 1
