with open("logs/modul_extracted_pure.txt", "r", encoding="utf-8") as f:
    full_text = " ".join([line.strip() for line in f])

import re
matches = [m.start() for m in re.finditer(r'Lab 2', full_text, re.IGNORECASE)]

print("Kemunculan Lab 2:", len(matches))
for i, pos in enumerate(matches):
    print(f"\n=== KEMUNCULAN {i+1} ===")
    start = max(0, pos - 50)
    end = min(len(full_text), pos + 1500)
    print(full_text[start:end])
