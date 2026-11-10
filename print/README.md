# Printable Workbook

`English-Fluency-OS-A4.pdf` is the whole curriculum as one printable A4 workbook: a contents page with page numbers, then each module on its own pages. Deck entries are numbered (F001, V001, E001, C001, PR01, SG01, CS01) and never split across two pages, and every file reference prints as a page reference. The trackers have space to write in. Print the Progress Tracker page once a week.

Single- or double-sided printing both work. Margins are even on both sides.

## Rebuilding after an edit

The PDF is generated from the Markdown files, so edit those, not the PDF. Then run, from the repository root:

```bash
pip install -r print/requirements.txt
python print/build_pdf.py
```

This overwrites `print/English-Fluency-OS-A4.pdf`. Add `--html preview.html` to also save the intermediate HTML, which helps with debugging the layout.

- **WeasyPrint** renders the PDF. On macOS and Windows it needs the Pango library first; see WeasyPrint's installation guide.
- **Fonts:** the layout uses Inter (free) and falls back to Carlito, DejaVu Sans, Segoe UI or Arial. Install Inter to match the committed PDF exactly.
- **Layout:** `style.css` controls it. `build_pdf.py` sets the module order and how each deck's fields print.
