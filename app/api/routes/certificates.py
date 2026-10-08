from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.certificate import Certificate
from app.utils.logger import logger

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}",
    summary="Download generated certificate PDF",
    description="Streams the generated PDF file for a specific certificate record.",
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Binary PDF stream of the certificate",
        },
        400: {"description": "Certificate is not yet generated or failed"},
        404: {"description": "Certificate record or physical file not found"},
    },
)
def download_certificate(
    certificate_id: str,
    inline: bool = Query(False, description="Preview inline in browser instead of downloading as attachment"),
    db: Session = Depends(get_db),
):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found",
        )

    if cert.status == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate generation is still pending or in progress",
        )

    if cert.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate generation failed: {cert.error_message or 'Unknown error'}",
        )

    if not cert.file_path or not Path(cert.file_path).exists():
        logger.error(f"Certificate file missing on disk: {cert.file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file is missing on storage disk",
        )

    safe_recipient_name = "".join(c for c in cert.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
    filename = f"Certificate_{safe_recipient_name.replace(' ', '_')}.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline" if inline else "attachment",
    )
