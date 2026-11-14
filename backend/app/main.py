from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

from .pdf_reader import MAX_FILE_SIZE, extract_pages, PdfError
from .analyzer import analyze_pages, InputSizeError
from .schemas import DecisionAnalysis

app = FastAPI(title="CivicScope API", version="0.1.0")


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
        pages = await run_in_threadpool(extract_pages, content)
        return await analyze_pages(pages)
    except PdfError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TimeoutError, APITimeoutError):
        raise HTTPException(status_code=504, detail="Analysis timed out. Please retry with a shorter PDF.")
    except AuthenticationError:
        raise HTTPException(status_code=503, detail="The analysis service credentials need attention. Contact the demo team.")
    except RateLimitError:
        raise HTTPException(status_code=503, detail="The analysis service is busy or its quota is exhausted. Please try again later.")
    except (APIConnectionError, APIStatusError):
        raise HTTPException(status_code=503, detail="The analysis provider is unavailable. Please try again later.")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InputSizeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError:
        # Do not leak arbitrary model/provider validation details to the browser.
        raise HTTPException(status_code=422, detail="The document could not be analyzed reliably. Please try a shorter, text-based municipal PDF.")
    except Exception:
        # Do not expose API keys, prompts or internal provider responses.
        return JSONResponse(status_code=422, content={"detail": "The document could not be analyzed reliably. Please try a shorter, text-based municipal PDF."})
