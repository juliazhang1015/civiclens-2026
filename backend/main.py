from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

from .pdf_reader import MAX_FILE_SIZE, extract_pages, PdfError
from .analyzer import analyze_pages
from .schemas import DecisionAnalysis

app = FastAPI(title="CivicScope API", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=DecisionAnalysis)
async def analyze(file: UploadFile = File(...)):
    try:
        if file.content_type not in {"application/pdf", "application/octet-stream"} and not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=415, detail="Only PDF documents are supported.")
        content = await file.read(MAX_FILE_SIZE + 1)
    finally:
        await file.close()

    try:
        pages = await run_in_threadpool(extract_pages, content)
        return await analyze_pages(pages)
    except PdfError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TimeoutError, APITimeoutError) as exc:
        raise HTTPException(status_code=504, detail="Analysis timed out. Please retry with a shorter PDF.") from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=503, detail="The analysis service credentials need attention. Contact the demo team.") from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=503, detail="The analysis service is busy or its quota is exhausted. Please try again later.") from exc
    except (APIConnectionError, APIStatusError) as exc:
        raise HTTPException(status_code=503, detail="The analysis provider is unavailable. Please try again later.") from exc
    except RuntimeError as exc:
        # RuntimeError messages may contain provider secrets; never echo them to clients.
        raise HTTPException(status_code=503, detail="The analysis service is not configured or is temporarily unavailable.") from exc
    except ValueError as exc:
        # analyzer.py currently raises this exact message for excessive extracted text.
        # Other ValueErrors (evidence or model validation) must remain generic.
        if str(exc).startswith("This document contains too much text"):
            raise HTTPException(status_code=413, detail="This PDF contains too much text. Upload a shorter document.") from exc
        raise HTTPException(status_code=422, detail="The document could not be analyzed reliably. Please try a shorter, text-based municipal PDF.") from exc
    except Exception:
        # Do not expose API keys, prompts, or internal provider responses.
        return JSONResponse(status_code=422, content={"detail": "The document could not be analyzed reliably. Please try a shorter, text-based municipal PDF."})
