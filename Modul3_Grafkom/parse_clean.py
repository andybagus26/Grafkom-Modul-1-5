import pypdf

reader = pypdf.PdfReader("docs/Module3_ID.pdf")
print("Total Halaman:", len(reader.pages))

with open("logs/modul_clean_text.txt", "w", encoding="utf-8") as out:
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        out.write(f"\n\n==================== HALAMAN {i+1} ====================\n\n")
        out.write(text if text else "")

print("Ekstraksi PDF selesai bersih!")
