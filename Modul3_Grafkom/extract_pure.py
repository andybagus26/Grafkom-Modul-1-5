import zlib
import re

with open("docs/Module3_ID.pdf", "rb") as f:
    pdf_data = f.read()

# Cari semua stream flatedecode di dalam PDF
stream_pattern = re.compile(rb'stream[\r\n]+(.*?)[\r\n]+endstream', re.DOTALL)
streams = stream_pattern.findall(pdf_data)

full_text = []

for s in streams:
    try:
        decompressed = zlib.decompress(s)
        # Ekstrak string di dalam tanda kurung (BT ... ET block)
        text_matches = re.findall(rb'\(([^\)\\]*(?:\\.[^\)\\]*)*)\)', decompressed)
        for tm in text_matches:
            # unescape
            cleaned = tm.replace(b'\\(', b'(').replace(b'\\)', b')').replace(b'\\\\', b'\\')
            try:
                line = cleaned.decode('utf-8')
            except UnicodeDecodeError:
                line = cleaned.decode('latin1', errors='ignore')
            if len(line.strip()) > 1:
                full_text.append(line.strip())
    except Exception:
        pass

result = "\n".join(full_text)
with open("logs/modul_extracted_pure.txt", "w", encoding="utf-8") as out:
    out.write(result)

print("Berhasil diekstrak murni! Total baris:", len(full_text))
