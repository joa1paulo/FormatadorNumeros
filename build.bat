@echo off
REM Gera dist\FormatadorContatos.exe (rode este arquivo na pasta do projeto, no Windows)

py -m pip install --upgrade pyinstaller fastapi uvicorn python-multipart
if errorlevel 1 goto erro

py -m PyInstaller --onefile --name FormatadorContatos ^
  --collect-submodules uvicorn ^
  --hidden-import multipart ^
  --hidden-import python_multipart ^
  launcher.py
if errorlevel 1 goto erro

echo.
echo Pronto! O executavel esta em: dist\FormatadorContatos.exe
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Copie a mensagem acima e me envie.
pause
exit /b 1