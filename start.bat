@echo off
echo Starting GraphRAG with AI Agents...
echo.

REM Check if Neo4j is running
docker ps | findstr neo4j > nul
if errorlevel 1 (
    echo Starting Neo4j...
    docker-compose up -d neo4j
    timeout /t 10 /nobreak > nul
) else (
    echo Neo4j already running
)

echo.
echo Starting FastAPI backend...
start "FastAPI" cmd /k "cd /d %~dp0 && python -m uvicorn app.main:app --reload"

timeout /t 3 /nobreak > nul

echo.
echo Starting Streamlit frontend...
start "Streamlit" cmd /k "cd /d %~dp0 && streamlit run app/streamlit_app.py"

echo.
echo Services starting...
echo - Neo4j: http://localhost:7474
echo - API: http://localhost:8000/docs
echo - Streamlit: http://localhost:8501
echo.
echo Press any key to exit (services will continue running)
pause > nul
