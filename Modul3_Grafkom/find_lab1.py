with open("logs/modul_extracted_pure.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f]

full_text = " ".join(lines)

# Cari di mana ada kata "Lab 1"
import re
matches = [m.start() for m in re.finditer(r'Lab 1', full_text, re.IGNORECASE)]

print("Ditemukan kemunculan Lab 1:", len(matches))
for i, pos in enumerate(matches):
    print(f"\n--- KEMUNCULAN {i+1} ---")
    start = max(0, pos - 100)
    end = min(len(full_text), pos + 1200)
    print(full_text[start:end])
