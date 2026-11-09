#!/usr/bin/env python3
import sys

def dump_pdf_text(pdf_path):
    # Coba modul bawaan python jika terinstall
    for mod_name in ['pypdf', 'fitz', 'pdfminer']:
        try:
            if mod_name == 'pypdf':
                import pypdf
                reader = pypdf.PdfReader(pdf_path)
                text = ""
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        text += f"\n--- HALAMAN {idx+1} ---\n" + t
                return text
            elif mod_name == 'fitz':
                import fitz
                doc = fitz.open(pdf_path)
                text = ""
                for idx, page in enumerate(doc):
                    text += f"\n--- HALAMAN {idx+1} ---\n" + page.get_text()
                return text
        except ImportError:
            continue

    # Fallback ekstraksi stream text sederhana
    with open(pdf_path, 'rb') as f:
        content = f.read()
    import re
    # cari string di dalam PDF
    strings = re.findall(rb'\(([^\)]{3,})\)', content)
    lines = [s.decode('latin1', errors='ignore') for s in strings if len(s) > 3]
    return "\n".join(lines[:200])

if __name__ == "__main__":
    t = dump_pdf_text("docs/Module3_ID.pdf")
    with open("logs/extracted_pdf.txt", "w") as out:
        out.write(t)
    print("Selesai mengekstrak. Karakter:", len(t))
