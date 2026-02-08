# GraphRAG Startup Script
Write-Host "Starting GraphRAG with AI Agents..." -ForegroundColor Cyan
Write-Host ""

# Check if Neo4j is running
$neo4jRunning = docker ps | Select-String "neo4j"
if (-not $neo4jRunning) {
    Write-Host "Starting Neo4j..." -ForegroundColor Yellow
    docker-compose up -d neo4j
    Start-Sleep -Seconds 10
} else {
    Write-Host "Neo4j already running" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting FastAPI backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python -m uvicorn app.main:app --reload"

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting Streamlit frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; streamlit run app/streamlit_app.py"

Write-Host ""
Write-Host "Services started:" -ForegroundColor Green
Write-Host "- Neo4j Browser: http://localhost:7474 (user: neo4j, pass: password123)"
Write-Host "- API Docs: http://localhost:8000/docs"
Write-Host "- Streamlit UI: http://localhost:8501"
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop services" -ForegroundColor Cyan
