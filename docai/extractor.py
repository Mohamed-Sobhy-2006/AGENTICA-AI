import io
import logging
import os
from pathlib import Path

import numpy as np
import pymupdf as fitz
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image

logger = logging.getLogger(__name__)

_OCR_ENGINE = None

_BLIP_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
_EMBED_ATTR = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
)


def _get_ocr_engine():
    """Lazy-load PaddleOCR for English documents with oneDNN/PIR workaround on Windows."""
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        from paddleocr import PaddleOCR

        try:
            _OCR_ENGINE = PaddleOCR(
                use_textline_orientation=True,
                lang="en",
                enable_mkldnn=False,
            )
        except TypeError:
            _OCR_ENGINE = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                enable_mkldnn=False,
            )
    return _OCR_ENGINE


def _prepare_image_for_ocr(img: Image.Image, max_dim: int = 2200) -> np.ndarray:
    """Convert image to RGB and downscale oversized images to protect RAM/CPU."""
    rgb_img = img.convert("RGB")
    if max(rgb_img.width, rgb_img.height) > max_dim:
        rgb_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return np.array(rgb_img)


def _run_paddle_ocr(image_input) -> tuple[str, float]:
    """Safely run PaddleOCR (v3.x or v2.x) and return (text, character_weighted_confidence)."""
    ocr = _get_ocr_engine()
    try:
        result = (
            ocr.predict(image_input)
            if hasattr(ocr, "predict")
            else ocr.ocr(image_input)
        )
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("PaddleOCR failed on image input: %s", exc)
        return "", 0.0

    lines: list[str] = []
    weighted_sum = 0.0
    total_chars = 0

    if not result:
        return "", 0.0

    first_item = result[0]
    if first_item is None:
        return "", 0.0

    if isinstance(first_item, dict) or hasattr(first_item, "get"):
        rec_texts = first_item.get("rec_texts") or []
        rec_scores = first_item.get("rec_scores") or []
        for raw_text, raw_score in zip(rec_texts, rec_scores):
            text_part = str(raw_text).strip()
            score = float(raw_score)
            if text_part:
                lines.append(text_part)
                char_len = len(text_part)
                weighted_sum += score * char_len
                total_chars += char_len

    elif isinstance(first_item, list):
        for line in first_item:
            if not line or len(line) < 2:
                continue
            text_part = str(line[1][0]).strip()
            score = float(line[1][1])
            if text_part:
                lines.append(text_part)
                char_len = len(text_part)
                weighted_sum += score * char_len
                total_chars += char_len

    full_text = "\n".join(lines)
    avg_conf = round(weighted_sum / total_chars, 4) if total_chars > 0 else 0.0
    return full_text, avg_conf


def _weighted_average(segments: list[tuple[str, float]]) -> float:
    """Compute confidence score weighted by the character length of each segment."""
    total_chars = sum(len(text) for text, _ in segments if text)
    if total_chars == 0:
        return 0.0
    weighted_sum = sum(len(text) * conf for text, conf in segments if text)
    return round(weighted_sum / total_chars, 4)


def extract_from_pdf(file_path: str, max_pages: int = 30) -> tuple[str, float]:
    """
    Extract text from a PDF using PyMuPDF (with reading-order sort).
    Automatically falls back to PaddleOCR for scanned/image-based pages (< 50 chars).
    """
    doc = fitz.open(file_path)
    segments: list[tuple[str, float]] = []

    for page_idx, page in enumerate(doc):
        if page_idx >= max_pages:
            break

        native_text = page.get_text("text", sort=True).strip()

        if len(native_text) >= 50:
            segments.append((native_text, 0.99))
        else:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_array = _prepare_image_for_ocr(img)
            ocr_text, ocr_conf = _run_paddle_ocr(img_array)
            if ocr_text:
                segments.append((ocr_text, ocr_conf))

    doc.close()
    combined_text = "\n\n".join(text for text, _ in segments).strip()
    return combined_text, _weighted_average(segments)


def extract_from_image(file_path: str) -> tuple[str, float]:
    """Extract text and confidence from an image file using PaddleOCR."""
    with Image.open(file_path) as img:
        img_array = _prepare_image_for_ocr(img)
    return _run_paddle_ocr(img_array)


def _extract_table_text(table: Table) -> str:
    """Extract rows from a Word table while skipping horizontally merged duplicate cells."""
    rows_out: list[str] = []
    for row in table.rows:
        seen_cells = set()
        unique_cells: list[str] = []
        for cell in row.cells:
            cell_id = id(cell._tc)
            if cell_id not in seen_cells:
                seen_cells.add(cell_id)
                clean_text = cell.text.strip()
                if clean_text:
                    unique_cells.append(clean_text)
        if unique_cells:
            rows_out.append(" | ".join(unique_cells))
    return "\n".join(rows_out)


def _extract_paragraph_images(
    paragraph: Paragraph, doc: Document
) -> list[tuple[str, float]]:
    """Extract and OCR any meaningful embedded images (>= 150x150 px) inside a paragraph."""
    image_segments: list[tuple[str, float]] = []
    for blip in paragraph._element.iter(_BLIP_TAG):
        rel_id = blip.get(_EMBED_ATTR)
        if not rel_id or rel_id not in doc.part.related_parts:
            continue
        image_part = doc.part.related_parts[rel_id]
        try:
            with Image.open(io.BytesIO(image_part.blob)) as img:
                if img.width < 150 or img.height < 150:
                    continue
                img_array = _prepare_image_for_ocr(img)
            ocr_text, ocr_conf = _run_paddle_ocr(img_array)
            if ocr_text:
                image_segments.append((ocr_text, ocr_conf))
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("Failed to run OCR on embedded image: %s", exc)
            continue
    return image_segments


def extract_from_docx(file_path: str) -> tuple[str, float]:
    """
    Extract text from a .docx file in exact document flow order:
    Headers -> Body (Paragraphs, inline Images via OCR, deduplicated Tables) -> Footers.
    """
    doc = Document(file_path)
    segments: list[tuple[str, float]] = []

    seen_headers = set()
    for section in doc.sections:
        header_lines = [
            p.text.strip() for p in section.header.paragraphs if p.text.strip()
        ]
        header_block = "\n".join(header_lines)
        if header_block and header_block not in seen_headers:
            seen_headers.add(header_block)
            segments.append((header_block, 1.0))

    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            para = Paragraph(child, doc)
            text = para.text.strip()
            if text:
                segments.append((text, 1.0))
            segments.extend(_extract_paragraph_images(para, doc))
        elif isinstance(child, CT_Tbl):
            table = Table(child, doc)
            table_text = _extract_table_text(table)
            if table_text:
                segments.append((table_text, 1.0))

    seen_footers = set()
    for section in doc.sections:
        footer_lines = [
            p.text.strip() for p in section.footer.paragraphs if p.text.strip()
        ]
        footer_block = "\n".join(footer_lines)
        if footer_block and footer_block not in seen_footers:
            seen_footers.add(footer_block)
            segments.append((footer_block, 1.0))

    combined_text = "\n\n".join(text for text, _ in segments).strip()
    return combined_text, _weighted_average(segments)


def extract_text(file_path: str) -> tuple[str, float]:
    """
    Main entry point: detect file extension and extract (raw_text, confidence_score).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_from_pdf(str(path))
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}:
        return extract_from_image(str(path))
    if ext == ".docx":
        return extract_from_docx(str(path))
    if ext in {".txt", ".md", ".csv", ".json"}:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        return text, (1.0 if text else 0.0)

    raise ValueError(f"Unsupported file format: {ext}")