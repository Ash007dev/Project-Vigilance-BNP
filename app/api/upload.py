from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/api/upload", tags=["upload"])

@router.post("")
async def upload_dataset(file: UploadFile = File(...)):
    return {
        "filename": file.filename,
        "status": "received",
        "next_step": "validation_and_ingestion",
    }
