#!/usr/bin/env python3
"""
Extract Figure 1..N images from a PDF using caption + layout heuristics.

Input source (mutually exclusive; default scans ./raw):
  --url URL            Direct PDF URL
  --pdf PATH           Single local PDF
  --input-dir DIR      Directory of local PDFs

Output:
  Per-PDF subfolder under --out (default: ./figures), e.g. figures/<pdf_stem>/figure_NN_pX.png

Dependencies:
  pip install pymupdf requests
"""

from __future__ import annotations

import argparse
import re
import statistics
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

import fitz  # PyMuPDF
import requests

DEFAULT_INPUT_DIR = "raw"
DEFAULT_OUTPUT_DIR = "figures"

CAPTION_RE = re.compile(r"\b(?:Figure|Fig\.?)\s*(\d+)\b", re.IGNORECASE)


def normalize_pdf_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("arxiv.org") and parsed.path.startswith("/html/"):
        paper_id = parsed.path.removeprefix("/html/").strip("/")
        if paper_id:
            return f"{parsed.scheme or 'https'}://{parsed.netloc}/pdf/{paper_id}.pdf"
    return url


def download_pdf(url: str, timeout: int = 30) -> bytes:
    url = normalize_pdf_url(url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "").lower()

    if "pdf" not in ctype and not url.lower().endswith(".pdf") and "octet-stream" not in ctype:
        raise ValueError(f"URL does not appear to be a PDF (content-type={ctype!r})")
    return resp.content


def sanitize_path_component(name: str) -> str:
    s = name.strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return s or "untitled-paper"


def title_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    base = Path(path).name or "paper.pdf"
    stem = Path(base).stem
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "untitled-paper"


def load_local_pdf(path: Path) -> bytes:
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    return path.read_bytes()


def iter_input_pdfs(args: argparse.Namespace) -> Iterator[Tuple[str, bytes, str]]:
    if args.url:
        print(f"[info] downloading: {args.url}")
        pdf_bytes = download_pdf(args.url, timeout=args.timeout)
        print(f"[info] downloaded {len(pdf_bytes):,} bytes")
        yield args.url, pdf_bytes, infer_paper_title(pdf_bytes, args.url)
        return

    if args.pdf:
        path = Path(args.pdf).resolve()
        pdf_bytes = load_local_pdf(path)
        yield str(path), pdf_bytes, sanitize_path_component(path.stem)
        return

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files in {input_dir}")

    print(f"[info] scanning {input_dir}: found {len(pdfs)} PDF(s)")
    for path in pdfs:
        yield str(path), load_local_pdf(path), sanitize_path_component(path.stem)


def infer_paper_title(pdf_bytes: bytes, url: str) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        meta_title = (doc.metadata or {}).get("title", "") or ""
        doc.close()
    except Exception:
        meta_title = ""

    meta_title = meta_title.strip()
    if meta_title and meta_title.lower() not in {"untitled", "microsoft word -", "title"}:
        return sanitize_path_component(meta_title)
    return sanitize_path_component(title_from_url(url))


def block_text(block: Dict) -> str:
    lines: List[str] = []
    for line in block.get("lines", []):
        txt = "".join(span.get("text", "") for span in line.get("spans", []))
        txt = txt.strip()
        if txt:
            lines.append(txt)
    return " ".join(lines).strip()


def rect_union(rects: Sequence[fitz.Rect]) -> fitz.Rect:
    x0 = min(r.x0 for r in rects)
    y0 = min(r.y0 for r in rects)
    x1 = max(r.x1 for r in rects)
    y1 = max(r.y1 for r in rects)
    return fitz.Rect(x0, y0, x1, y1)


def rect_distance(a: fitz.Rect, b: fitz.Rect) -> Tuple[float, float]:
    dx = max(0.0, max(a.x0, b.x0) - min(a.x1, b.x1))
    dy = max(0.0, max(a.y0, b.y0) - min(a.y1, b.y1))
    return dx, dy


def horizontal_overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    overlap = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    return overlap / max(1.0, min(a.width, b.width))


def is_likely_caption(text: str, match: re.Match[str], rect: fitz.Rect) -> bool:
    words = len(text.split())
    if words < 4 or words > 180:
        return False
    if rect.height > 110:
        return False

    prefix = text[: match.start()].strip()
    if prefix:
        if len(prefix.split()) > 5:
            return False
        if any(ch in prefix for ch in ".:;!?"):
            return False

    after = text[match.end() :].lstrip()
    if after and after[0].islower():
        # Typical in-body reference: "... in Figure 2 we ..."
        return False

    return True


def find_caption_blocks(page: fitz.Page, text_dict: Dict) -> List[Tuple[int, fitz.Rect, str]]:
    captions: List[Tuple[int, fitz.Rect, str]] = []

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue

        text = block_text(block)
        if not text:
            continue

        match = CAPTION_RE.search(text)
        if not match:
            continue

        rect = fitz.Rect(block["bbox"])
        if not is_likely_caption(text, match, rect):
            continue

        fig_no = int(match.group(1))
        captions.append((fig_no, rect, text))

    captions.sort(key=lambda x: (x[1].y0, x[1].x0))
    return captions


def collect_body_text_rects(text_dict: Dict, page_rect: fitz.Rect) -> List[fitz.Rect]:
    rects: List[fitz.Rect] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue

        txt = block_text(block)
        if len(txt.split()) < 5:
            continue

        r = fitz.Rect(block["bbox"])
        if r.width < page_rect.width * 0.12:
            continue
        if r.width > page_rect.width * 0.92:
            continue
        if r.height > page_rect.height * 0.35:
            continue
        rects.append(r)

    return rects


def infer_two_columns(page_rect: fitz.Rect, text_dict: Dict) -> Optional[Tuple[fitz.Rect, fitz.Rect]]:
    rects = collect_body_text_rects(text_dict, page_rect)
    if len(rects) < 8:
        return None

    page_width = page_rect.width
    narrow_rects = [
        r for r in rects if page_width * 0.18 <= r.width <= page_width * 0.48 and r.height <= page_rect.height * 0.18
    ]
    mid = page_rect.x0 + page_rect.width / 2

    def build_columns(candidates: Sequence[fitz.Rect]) -> Optional[Tuple[fitz.Rect, fitz.Rect]]:
        left = [r for r in candidates if (r.x0 + r.x1) / 2 < mid]
        right = [r for r in candidates if (r.x0 + r.x1) / 2 >= mid]
        if len(left) < 3 or len(right) < 3:
            return None

        left_x0 = statistics.median(r.x0 for r in left)
        left_x1 = statistics.median(r.x1 for r in left)
        right_x0 = statistics.median(r.x0 for r in right)
        right_x1 = statistics.median(r.x1 for r in right)
        left_width = statistics.median(r.width for r in left)
        right_width = statistics.median(r.width for r in right)
        gutter = right_x0 - left_x1

        if gutter < max(12.0, page_width * 0.015):
            return None
        if left_width > page_width * 0.55 or right_width > page_width * 0.55:
            return None
        if left_x1 >= mid + page_width * 0.08:
            return None
        if right_x0 <= mid - page_width * 0.08:
            return None

        margin = 10.0
        left_rect = fitz.Rect(
            max(page_rect.x0 + margin, left_x0 - 6.0),
            page_rect.y0,
            min(mid - 4.0, left_x1 + 6.0),
            page_rect.y1,
        )
        right_rect = fitz.Rect(
            max(mid + 4.0, right_x0 - 6.0),
            page_rect.y0,
            min(page_rect.x1 - margin, right_x1 + 6.0),
            page_rect.y1,
        )

        if left_rect.width < 40 or right_rect.width < 40:
            return None
        return left_rect, right_rect

    if len(narrow_rects) >= 6:
        two_cols = build_columns(narrow_rects)
        if two_cols is not None:
            return two_cols

    return build_columns(rects)


def detect_document_column_mode(
    doc: fitz.Document,
    sample_pages: int = 8,
) -> Tuple[str, int, int]:
    detected_double = 0
    checked_pages = 0

    for page_index in range(len(doc)):
        if checked_pages >= sample_pages:
            break

        page = doc[page_index]
        text_dict = page.get_text("dict")
        body_rects = collect_body_text_rects(text_dict, page.rect)
        if len(body_rects) < 8:
            continue

        checked_pages += 1
        if infer_two_columns(page.rect, text_dict) is not None:
            detected_double += 1

    if checked_pages == 0:
        return "single", 0, 0

    mode = "double" if detected_double >= max(2, (checked_pages + 1) // 2) else "single"
    return mode, detected_double, checked_pages


def infer_column_rect(page: fitz.Rect, caption_rect: fitz.Rect, text_dict: Dict) -> Tuple[fitz.Rect, bool]:
    margin = 10.0
    full_rect = fitz.Rect(page.x0 + margin, page.y0, page.x1 - margin, page.y1)
    two_cols = infer_two_columns(page, text_dict)

    if two_cols is None:
        # Fallback to simple midpoint split.
        full_width = caption_rect.width >= page.width * 0.65
        if full_width:
            return full_rect, True

        mid = page.x0 + page.width / 2
        center_x = (caption_rect.x0 + caption_rect.x1) / 2
        if center_x < mid:
            return fitz.Rect(page.x0 + margin, page.y0, mid - 8.0, page.y1), False
        return fitz.Rect(mid + 8.0, page.y0, page.x1 - margin, page.y1), False

    left_rect, right_rect = two_cols
    overlap_left = horizontal_overlap_ratio(caption_rect, left_rect)
    overlap_right = horizontal_overlap_ratio(caption_rect, right_rect)
    crosses_gutter = caption_rect.x0 <= left_rect.x1 and caption_rect.x1 >= right_rect.x0
    spans_both = (overlap_left >= 0.3 and overlap_right >= 0.3) or crosses_gutter
    if spans_both or caption_rect.width >= page.width * 0.62:
        return full_rect, True

    split = (left_rect.x1 + right_rect.x0) / 2
    center_x = (caption_rect.x0 + caption_rect.x1) / 2
    if center_x < split:
        return left_rect, False
    return right_rect, False


def infer_column_rect_with_mode(
    page: fitz.Rect,
    caption_rect: fitz.Rect,
    text_dict: Dict,
    column_mode: str,
) -> Tuple[fitz.Rect, bool]:
    margin = 10.0
    full_rect = fitz.Rect(page.x0 + margin, page.y0, page.x1 - margin, page.y1)

    if column_mode == "single":
        return full_rect, True
    if column_mode == "auto":
        return infer_column_rect(page, caption_rect, text_dict)

    # Forced double-column mode.
    two_cols = infer_two_columns(page, text_dict)
    if two_cols is None:
        mid = page.x0 + page.width / 2
        two_cols = (
            fitz.Rect(page.x0 + margin, page.y0, mid - 8.0, page.y1),
            fitz.Rect(mid + 8.0, page.y0, page.x1 - margin, page.y1),
        )
    left_rect, right_rect = two_cols
    overlap_left = horizontal_overlap_ratio(caption_rect, left_rect)
    overlap_right = horizontal_overlap_ratio(caption_rect, right_rect)
    crosses_gutter = caption_rect.x0 <= left_rect.x1 and caption_rect.x1 >= right_rect.x0
    if (overlap_left >= 0.3 and overlap_right >= 0.3) or crosses_gutter:
        return full_rect, True
    center_x = (caption_rect.x0 + caption_rect.x1) / 2
    split = (left_rect.x1 + right_rect.x0) / 2
    if center_x < split:
        return left_rect, False
    return right_rect, False


def collect_graphic_rects(page: fitz.Page, text_dict: Dict) -> List[fitz.Rect]:
    rects: List[fitz.Rect] = []

    for block in text_dict.get("blocks", []):
        if block.get("type") == 1:
            r = fitz.Rect(block["bbox"])
            if r.get_area() >= 120.0:
                rects.append(r)

    for r in page.cluster_drawings():
        rr = fitz.Rect(r)
        if rr.get_area() >= 120.0:
            rects.append(rr)

    return rects


def connected_region(
    anchor: fitz.Rect,
    candidates: Sequence[fitz.Rect],
    gap_x: float,
    gap_y: float,
) -> fitz.Rect:
    selected: List[fitz.Rect] = [anchor]
    changed = True

    while changed:
        changed = False
        union = rect_union(selected)
        for r in candidates:
            if any(r == s for s in selected):
                continue
            dx, dy = rect_distance(union, r)
            if dx <= gap_x and dy <= gap_y:
                selected.append(r)
                changed = True

    return rect_union(selected)


def pick_figure_clip(
    page: fitz.Page,
    caption_rect: fitz.Rect,
    graphic_rects: Sequence[fitz.Rect],
    text_dict: Dict,
    column_mode: str,
    max_upward: float,
    caption_padding: float,
    include_caption: bool,
) -> Optional[fitz.Rect]:
    page_rect = page.rect
    column_rect, is_full_width = infer_column_rect_with_mode(
        page_rect, caption_rect, text_dict, column_mode=column_mode
    )

    def filter_candidates(target_rect: fitz.Rect, min_overlap: float) -> List[fitz.Rect]:
        out: List[fitz.Rect] = []
        for r in graphic_rects:
            if r.y1 > caption_rect.y0 + 8:
                continue
            if r.y1 < caption_rect.y0 - max_upward:
                continue
            if horizontal_overlap_ratio(r, target_rect) < min_overlap:
                continue
            out.append(r)
        return out

    candidates = filter_candidates(column_rect, min_overlap=0.15)

    if not candidates:
        # If the chosen column was wrong, retry with full width.
        full_rect = fitz.Rect(page_rect.x0 + 10.0, page_rect.y0, page_rect.x1 - 10.0, page_rect.y1)
        candidates = filter_candidates(full_rect, min_overlap=0.05)
        if not candidates:
            return None
        column_rect = full_rect
        is_full_width = True

    anchor = max(candidates, key=lambda r: (r.y1, r.get_area()))
    band_top = max(page_rect.y0, anchor.y0 - max_upward)
    near_candidates = [r for r in candidates if r.y1 >= band_top]

    gap_x = 120.0 if is_full_width else 40.0
    gap_y = 30.0
    region = connected_region(anchor, near_candidates, gap_x=gap_x, gap_y=gap_y)

    # Keep the region in the inferred column and include the caption area.
    x0 = max(page_rect.x0, column_rect.x0 - 4.0, region.x0 - 4.0)
    x1 = min(page_rect.x1, column_rect.x1 + 4.0, region.x1 + 4.0)
    y0 = max(page_rect.y0, region.y0 - 4.0)
    if include_caption:
        y1 = min(page_rect.y1, max(region.y1 + 4.0, caption_rect.y1 + caption_padding))
    else:
        y1 = min(page_rect.y1, min(region.y1 + 4.0, caption_rect.y0 - caption_padding))
    clip = fitz.Rect(x0, y0, x1, y1)

    if clip.width < 20 or clip.height < 20:
        return None
    return clip


def fallback_clip(
    page: fitz.Page,
    caption_rect: fitz.Rect,
    text_dict: Dict,
    column_mode: str,
    max_upward: float,
    caption_padding: float,
    include_caption: bool,
) -> fitz.Rect:
    page_rect = page.rect
    column_rect, _ = infer_column_rect_with_mode(
        page_rect, caption_rect, text_dict, column_mode=column_mode
    )

    if include_caption:
        y1 = min(page_rect.y1, max(page_rect.y0 + 20.0, caption_rect.y1 + caption_padding))
    else:
        y1 = min(page_rect.y1, max(page_rect.y0 + 20.0, caption_rect.y0 - caption_padding))
    y0 = max(page_rect.y0, y1 - max_upward)

    return fitz.Rect(column_rect.x0, y0, column_rect.x1, y1)


def render_clip_png(page: fitz.Page, clip: fitz.Rect, scale: float = 3.0) -> bytes:
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    return pix.tobytes("png")


def save_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def extract_figures(
    pdf_bytes: bytes,
    out_dir: Path,
    overwrite: bool = False,
    caption_padding: float = 8.0,
    column_mode: str = "auto",
    include_caption: bool = True,
) -> Tuple[List[Path], str, int]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    saved: List[Path] = []
    skipped = 0
    seen_figs: set[int] = set()
    effective_column_mode = column_mode

    if column_mode == "auto":
        effective_column_mode, detected_double, checked_pages = detect_document_column_mode(doc)
        if checked_pages == 0:
            print("[info] column mode: auto -> single (insufficient text blocks for detection)")
        else:
            print(
                "[info] column mode: "
                f"auto -> {effective_column_mode} "
                f"(double-column pages: {detected_double}/{checked_pages})"
            )
    else:
        print(f"[info] column mode: forced {column_mode}")

    for page_index in range(len(doc)):
        page = doc[page_index]
        text_dict = page.get_text("dict")
        captions = find_caption_blocks(page, text_dict)
        if not captions:
            continue

        graphic_rects = collect_graphic_rects(page, text_dict)
        max_upward = max(220.0, page.rect.height * 0.55)

        for fig_no, cap_rect, cap_text in captions:
            if fig_no in seen_figs and not overwrite:
                continue

            clip = pick_figure_clip(
                page,
                cap_rect,
                graphic_rects,
                text_dict=text_dict,
                column_mode=effective_column_mode,
                max_upward=max_upward,
                caption_padding=caption_padding,
                include_caption=include_caption,
            )
            source = "detected graphics"
            if clip is None:
                clip = fallback_clip(
                    page,
                    cap_rect,
                    text_dict=text_dict,
                    column_mode=effective_column_mode,
                    max_upward=max_upward,
                    caption_padding=caption_padding,
                    include_caption=include_caption,
                )
                source = "fallback crop"
            elif include_caption:
                clip.y1 = min(page.rect.y1, max(clip.y1, cap_rect.y1 + caption_padding))

            out_path = out_dir / f"figure_{fig_no:02d}_p{page_index + 1}.png"
            if out_path.exists() and not overwrite:
                print(f"[skip] Figure {fig_no} already exists: {out_path}")
                skipped += 1
                continue

            png_data = render_clip_png(page, clip, scale=3.0)
            save_bytes(out_path, png_data)
            saved.append(out_path)
            seen_figs.add(fig_no)
            print(f"[saved] Figure {fig_no} from {source}: {out_path}")

    doc.close()
    return saved, effective_column_mode, skipped


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract Figure 1..N images from a PDF (local file, directory, or URL)",
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument("--url", help="Direct PDF URL")
    src.add_argument("--pdf", help="Path to a single local PDF file")
    src.add_argument(
        "--input-dir",
        help=f"Directory of local PDFs to process (default: ./{DEFAULT_INPUT_DIR} when no other source is given)",
    )
    p.add_argument(
        "--out",
        default=DEFAULT_OUTPUT_DIR,
        help="Parent directory where {paper_title}/ subfolders will be created",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds (URL mode)")
    p.add_argument(
        "--caption-padding",
        type=float,
        default=8.0,
        help="Extra points to include below the detected caption bbox",
    )
    p.add_argument(
        "--no-title-subdir",
        action="store_true",
        help="Save directly to --out without creating a per-PDF {paper_title}/ subfolder",
    )
    p.add_argument(
        "--column-mode",
        choices=["auto", "single", "double"],
        default="auto",
        help="Column inference mode for 2-column papers",
    )
    p.add_argument(
        "--exclude-caption",
        action="store_true",
        help="Crop only the figure body and exclude the caption text area",
    )
    args = p.parse_args()
    if not args.url and not args.pdf and not args.input_dir:
        args.input_dir = DEFAULT_INPUT_DIR
    return args


def main() -> int:
    args = parse_args()
    out_root = Path(args.out).resolve()

    total_saved = 0
    total_skipped = 0
    pdf_count = 0
    productive_pdfs = 0
    for label, pdf_data, paper_title in iter_input_pdfs(args):
        pdf_count += 1
        out_dir = out_root if args.no_title_subdir else (out_root / paper_title)
        print(f"[info] processing: {label}")
        print(f"[info] output directory: {out_dir}")

        try:
            saved, effective_column_mode, skipped = extract_figures(
                pdf_data,
                out_dir=out_dir,
                overwrite=args.overwrite,
                caption_padding=args.caption_padding,
                column_mode=args.column_mode,
                include_caption=not args.exclude_caption,
            )
        except Exception as exc:
            print(f"[warn] failed to extract from {label}: {exc}")
            continue

        if not saved and not skipped:
            print(f"[warn] no figure captions confidently detected in {label}")
            continue

        total_saved += len(saved)
        total_skipped += skipped
        productive_pdfs += 1
        print(
            f"[ok] {paper_title}: saved {len(saved)} new, skipped {skipped} existing -> {out_dir} "
            f"(layout={effective_column_mode})"
        )

    if productive_pdfs == 0:
        print("[warn] no figures detected across any input PDF")
        return 1

    print(
        f"[done] {total_saved} new figure(s) saved, {total_skipped} already present "
        f"across {pdf_count} PDF(s) -> {out_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
