from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .pdf_reader import MAX_FILE_SIZE, extract_pages, PdfError
from .analyzer import analyze_pages
from .schemas import DecisionAnalysis

app = FastAPI(title="CivicLens API", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=DecisionAnalysis)
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF documents are supported.")
    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()
    try:
        pages = extract_pages(content)
        return await analyze_pages(pages)
    except PdfError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        # Do not expose API keys, prompts or internal provider responses.
        return JSONResponse(status_code=422, content={"detail": "The document could not be analyzed reliably. Please try a shorter, text-based municipal PDF."})
