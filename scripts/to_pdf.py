#!/usr/bin/env python3
"""Markdown → PDF 変換"""
import sys
import markdown
from weasyprint import HTML

md_path = sys.argv[1]
pdf_path = md_path.replace(".md", ".pdf")

with open(md_path, encoding="utf-8") as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

html_full = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 25mm 20mm; }}
  body {{ font-family: "Noto Sans CJK JP", "Hiragino Sans", sans-serif; font-size: 11pt; line-height: 1.7; color: #1a1a1a; }}
  h1 {{ font-size: 22pt; border-bottom: 3px solid #333; padding-bottom: 8px; margin-top: 30px; }}
  h2 {{ font-size: 16pt; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 25px; color: #2c3e50; }}
  h3 {{ font-size: 13pt; margin-top: 18px; color: #34495e; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; font-size: 10pt; }}
  th {{ background: #f5f5f5; font-weight: bold; }}
  code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-size: 10pt; }}
  pre {{ background: #f8f8f8; padding: 14px; border-radius: 6px; border: 1px solid #e0e0e0; font-size: 10pt; line-height: 1.5; white-space: pre-wrap; }}
  hr {{ border: none; border-top: 2px solid #e0e0e0; margin: 20px 0; }}
  p {{ margin: 6px 0; }}
</style>
</head><body>{html_body}</body></html>"""

HTML(string=html_full).write_pdf(pdf_path)
print(pdf_path)
