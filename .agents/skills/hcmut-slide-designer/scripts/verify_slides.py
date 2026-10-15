#!/usr/bin/env python3
"""
verify_slides.py - QA and Verification Utility for HCMUT Beamer Slides

Subcommands:
  check-log   Scan a LaTeX .log file for Overfull \\vbox, Overfull \\hbox, and errors.
  render      Render PDF pages to PNG images for visual inspection using PyMuPDF.
  compile     Compile a .tex file with xelatex (2 passes) and verify .log cleanly.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def check_log_file(log_path: Path) -> int:
    """Scans LaTeX log file for overfull warnings and errors."""
    if not log_path.exists():
        print(f"Error: Log file not found at {log_path}")
        return 1

    content = log_path.read_text(encoding="utf-8", errors="ignore")

    vbox_warnings = re.findall(r"Overfull \\vbox \(([^)]+)\) has occurred while \\output is active", content)
    hbox_warnings = re.findall(r"Overfull \\hbox \(([^)]+)\) in paragraph at lines (\d+--\d+)", content)
    errors = [line for line in content.splitlines() if line.startswith("!") or "Fatal error" in line]

    print(f"=== LaTeX Log Audit Report for: {log_path.name} ===")
    has_critical = False

    if errors:
        has_critical = True
        print(f"[FAILED] Found {len(errors)} LaTeX error(s):")
        for err in errors[:5]:
            print(f"  - {err}")

    if vbox_warnings:
        has_critical = True
        print(f"[FAILED] Found {len(vbox_warnings)} Overfull \\vbox warning(s) (Slide vertical overflow):")
        for vb in vbox_warnings:
            print(f"  - Overfull \\vbox: {vb}")
    else:
        print("[PASSED] Zero Overfull \\vbox warnings. Slide vertical boundaries are safe.")

    if hbox_warnings:
        print(f"[WARNING] Found {len(hbox_warnings)} Overfull \\hbox warning(s) (Table/text width overflow):")
        for hb, lines in hbox_warnings[:5]:
            print(f"  - {hb} at lines {lines}")
    else:
        print("[PASSED] Zero Overfull \\hbox warnings.")

    return 1 if has_critical else 0


def render_pdf_to_png(pdf_path: Path, out_dir: Path, dpi: int = 150, pages: list[int] | None = None) -> int:
    """Renders PDF pages to PNG images using PyMuPDF."""
    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return 1

    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: PyMuPDF (fitz) is not installed. Run: pip install pymupdf")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    print(f"Rendering {pdf_path.name} ({total_pages} total pages) to {out_dir} at {dpi} DPI...")

    target_pages = pages if pages is not None else list(range(1, total_pages + 1))
    rendered_count = 0

    for page_num in target_pages:
        if 1 <= page_num <= total_pages:
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=dpi)
            out_file = out_dir / f"slide_{page_num:02d}.png"
            pix.save(str(out_file))
            rendered_count += 1

    print(f"Successfully rendered {rendered_count} slide image(s) to: {out_dir}")
    return 0


def compile_tex(tex_path: Path, passes: int = 2) -> int:
    """Compiles .tex file using xelatex for the specified number of passes."""
    if not tex_path.exists():
        print(f"Error: TeX file not found at {tex_path}")
        return 1

    cwd = tex_path.parent
    tex_filename = tex_path.name
    log_path = tex_path.with_suffix(".log")

    print(f"Compiling {tex_filename} with xelatex ({passes} passes)...")
    for p in range(1, passes + 1):
        print(f"Pass {p}/{passes}...")
        res = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", tex_filename],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if res.returncode != 0:
            print(f"Compilation failed on pass {p} with exit code {res.returncode}")
            return check_log_file(log_path)

    print("Compilation completed successfully.")
    return check_log_file(log_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="HCMUT Beamer Slide Verification Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: check-log
    p_check = subparsers.add_parser("check-log", help="Scan .log file for errors and overfull warnings")
    p_check.add_argument("--log", type=Path, default=Path("docs/slides_hcmut.log"), help="Path to .log file")

    # Subcommand: render
    p_render = subparsers.add_parser("render", help="Render PDF slides to PNG images for visual QA")
    p_render.add_argument("--pdf", type=Path, default=Path("docs/slides_hcmut.pdf"), help="Path to .pdf file")
    p_render.add_argument("--out-dir", type=Path, default=Path("docs/preview_slides"), help="Output directory for PNGs")
    p_render.add_argument("--dpi", type=int, default=150, help="Image DPI resolution (default: 150)")
    p_render.add_argument("--pages", type=int, nargs="*", help="Specific 1-indexed pages to render (default: all)")

    # Subcommand: compile
    p_compile = subparsers.add_parser("compile", help="Compile .tex with xelatex and audit .log")
    p_compile.add_argument("--tex", type=Path, default=Path("docs/slides_hcmut.tex"), help="Path to .tex file")
    p_compile.add_argument("--passes", type=int, default=2, help="Number of compilation passes (default: 2)")

    args = parser.parse_args()

    if args.command == "check-log":
        sys.exit(check_log_file(args.log))
    elif args.command == "render":
        sys.exit(render_pdf_to_png(args.pdf, args.out_dir, args.dpi, args.pages))
    elif args.command == "compile":
        sys.exit(compile_tex(args.tex, args.passes))


if __name__ == "__main__":
    main()
