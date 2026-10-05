import os
import uuid
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Optional
from app.core.config import settings

router = APIRouter(prefix="/api/uploads", tags=["File Uploads"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for high-res gallery images

# Configure Cloudinary if environment variables exist
has_cloudinary = bool(
    settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET
)

if has_cloudinary:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


@router.post("/file")
async def upload_file(file: UploadFile = File(...), folder: Optional[str] = Form("shepherd_media")):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    if has_cloudinary:
        try:
            resource_type = "raw" if ext in [".pdf", ".doc", ".docx"] else "image"
            file_uuid = uuid.uuid4().hex
            # Preserve extension in public_id so Cloudinary generates URLs ending with .pdf
            public_id_with_ext = f"{file_uuid}{ext}"

            upload_result = cloudinary.uploader.upload(
                content,
                folder=f"shepherd_network/{folder}",
                public_id=public_id_with_ext,
                resource_type=resource_type,
                type="upload",
                access_mode="public",
            )
            return {
                "filename": file.filename,
                "url": upload_result.get("secure_url"),
                "public_id": upload_result.get("public_id"),
                "resource_type": resource_type,
                "size_bytes": len(content),
                "provider": "cloudinary",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

    # Fallback to local storage if Cloudinary is not configured in local environment
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": unique_name,
        "url": f"/uploads/{unique_name}",
        "size_bytes": len(content),
        "provider": "local_fallback"
    }


@router.post("/gallery")
async def upload_gallery_files(files: List[UploadFile] = File(...)):
    uploaded_urls = []
    for file in files:
        res = await upload_file(file=file, folder="galleries")
        uploaded_urls.append(res["url"])

    return {
        "urls": uploaded_urls,
        "count": len(uploaded_urls)
    }