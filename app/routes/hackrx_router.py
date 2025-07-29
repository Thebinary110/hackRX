from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List
from src.pipeline.run_pipeline import process_file

hackrx_router = APIRouter(prefix="/api/v1/hackrx", tags=["HackRx"])

@hackrx_router.post("/ask")
async def ask_questions(
    file: UploadFile = File(...),
    questions: List[str] = Form(...)
):
    file_bytes = await file.read()
    answers = process_file(file_bytes, file.filename, questions)
    return JSONResponse(content={"answers": answers})
