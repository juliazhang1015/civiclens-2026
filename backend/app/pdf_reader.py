import fitz

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_PAGES = 25


class PdfError(ValueError):
    pass


def extract_pages(content: bytes) -> list[str]:
    if not content or len(content) > MAX_FILE_SIZE:
        raise PdfError("Please upload a PDF smaller than 10 MB.")
    if not content.startswith(b"%PDF-"):
        raise PdfError("The selected file is not a valid PDF.")
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            if document.is_encrypted:
                raise PdfError("Password-protected PDFs are not supported.")
            if document.page_count > MAX_PAGES:
                raise PdfError(f"Please upload a document with at most {MAX_PAGES} pages.")
            pages = [page.get_text(sort=True).strip() for page in document]
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError("Unable to read this PDF.") from exc
    if not any(pages):
        raise PdfError("No selectable text found. Scanned PDFs are not supported yet.")
    return pages
