"""HTTP boundary for municipal PDF analysis. No AI logic belongs here."""

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from starlette.concurrency import run_in_threadpool

from .analyzer import analyze_pages
from .pdf_reader import MAX_FILE_SIZE, PdfError, extract_pages
from .schemas import DecisionAnalysis

logger = logging.getLogger(__name__)
app = FastAPI(title="CivicScope API", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=DecisionAnalysis)
async def analyze(file: UploadFile = File(...)):
    try:
        filename = (file.filename or "").lower()
        if file.content_type not in {"application/pdf", "application/octet-stream"} and not filename.endswith(".pdf"):
            raise HTTPException(status_code=415, detail="Only PDF documents are supported.")
        # One extra byte lets extract_pages detect an oversized file safely.
        content = await file.read(MAX_FILE_SIZE + 1)
    finally:
        await file.close()

    try:
        pages = await run_in_threadpool(extract_pages, content)
        return await analyze_pages(pages)  # async API call: must await
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
        # Only expose the known actionable configuration error; other runtime
        # errors could contain provider internals or secret information.
        if str(exc).startswith("OPENAI_API_KEY is not configured"):
            raise HTTPException(status_code=503, detail="AI analysis is not configured. Ask the demo team to set OPENAI_API_KEY on the server.") from exc
        logger.exception("Unexpected runtime error during PDF analysis")
        raise HTTPException(status_code=503, detail="Analysis is temporarily unavailable. Please try again later.") from exc
    except ValueError as exc:
        # The analyzer has an explicit input text limit. Other ValueErrors (e.g.
        # evidence mismatches) indicate an unreliable result, not user fault.
        if str(exc).startswith("This document contains too much text"):
            raise HTTPException(status_code=413, detail="The PDF contains too much extracted text. Please upload a shorter document.") from exc
        logger.warning("Analyzer rejected an unreliable result: %s", type(exc).__name__)
        raise HTTPException(status_code=422, detail="The document could not be analyzed reliably. Try a shorter, text-based municipal PDF.") from exc
    except Exception as exc:
        logger.exception("Unexpected analysis error")
        raise HTTPException(status_code=422, detail="The document could not be analyzed reliably. Try a shorter, text-based municipal PDF.") from exc
