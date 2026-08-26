@echo off
echo ==============================================
echo Inciando o Sistema de Controle de Quadrinhos...
echo ==============================================

echo Verificando dependencias...
pip install -r requirements.txt

echo.
echo Iniciando o servidor web local (Nova Arquitetura)...
echo O site abrira no seu navegador em breve.
echo Pressione CTRL+C nesta janela para parar o servidor.
echo.

start http://127.0.0.1:8000
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
