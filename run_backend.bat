@echo off
echo Starting Cygnus FastAPI backend...
call cygnusVenv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
