import argparse
import sys
import warnings
from pathlib import Path
import cv2
import numpy as np
import easyocr
from ebooklib import epub


warnings.filterwarnings("ignore", message=".*pin_memory.*")

SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
LINE_DIST = 20

CSS = """
body { font-family: Georgia, serif; line-height: 1.6; max-width: 700px; margin: 2rem auto; padding: 0.1rem; }
h1, h2 { text-align: center; font-weight: normal; }
p { text-align: justify; text-indent: 1.5em; margin: 0.5em 0; }
"""


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def clean_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if np.mean(gray) < 127:
        gray = cv2.bitwise_not(gray)
    
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
    return cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 15
    )


def order_blocks(blocks):
    if not blocks:
        return blocks
    
    by_y = sorted(blocks, key=lambda x: x[0][0][1])
    
    rows = []
    current = [by_y[0]]
    cur_y = by_y[0][0][0][1]
    
    for b in by_y[1:]:
        y = b[0][0][1]
        if abs(y - cur_y) <= LINE_DIST:
            current.append(b)
        else:
            rows.append(current)
            current = [b]
            cur_y = y
    rows.append(current)
    
    result = []
    for row in rows:
        result.extend(sorted(row, key=lambda x: x[0][0][0]))
    
    return result


def ocr_file(path, reader):
    print(f"Обработка: {path.name}")
    
    img = cv2.imread(str(path))
    if img is None:
        print(f"  Не удалось открыть: {path}")
        return ""
    
    processed = clean_image(img)
    data = reader.readtext(processed, paragraph=False, detail=1)
    
    if not data:
        print("  Текст не найден")
        return ""
    
    ordered = order_blocks(data)
    text = "\n".join([x[1] for x in ordered])
    
    print(f"  Распознано {len(text.split())} слов")
    return text.strip()


def build_book(pages, output, title, author, lang):
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language(lang)
    book.add_author(author)
    
    style = epub.EpubItem("style", "style.css", "text/css", CSS)
    book.add_item(style)
    
    first = epub.EpubHtml("Титул", "title.xhtml", lang)
    first.content = f"<h1>{escape_html(title)}</h1><p style='text-align:center'><em>{escape_html(author)}</em></p>"
    first.add_item(style)
    book.add_item(first)
    
    book.add_item(epub.EpubNcx())
    
    nav = epub.EpubNav()
    nav.add_item(style)
    book.add_item(nav)
    
    spine_items = ["nav", first]
    
    for i, (name, text) in enumerate(pages, 1):
        fname = f"ch_{i:03d}.xhtml"
        ch = epub.EpubHtml(title=name, file_name=fname, lang=lang)
        
        paras = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                paras.append(f"<p>{escape_html(line)}</p>")
            else:
                paras.append("<p>&nbsp;</p>")
        
        ch.content = f"<h2>{escape_html(name)}</h2>" + "".join(paras)
        ch.add_item(style)
        
        book.add_item(ch)
        spine_items.append(ch)
    
    book.spine = spine_items
    
    epub.write_epub(str(output), book)
    


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--author", default="Неизвестный")
    parser.add_argument("--lang", default="ru,en")
    parser.add_argument("--epub-lang", default="ru")
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--keep-txt", action="store_true")
    args = parser.parse_args()
    
    files = []
    for p in args.images:
        if not p.exists():
            print(f"Предупреждение: файл не найден {p}")
            continue
        if p.suffix.lower() not in SUPPORTED:
            print(f"Предупреждение: неподдерживаемый формат {p.suffix}")
            continue
        files.append(p)
    
    if not files:
        print("Ошибка: нет файлов для обработки")
        sys.exit(1)
    
    langs = [x.strip() for x in args.lang.split(",")]
    print(f"Загрузка EasyOCR ({langs})...")
    
    try:
        reader = easyocr.Reader(langs, gpu=args.gpu)
    except Exception as e:
        print(f"Ошибка загрузки OCR: {e}")
        sys.exit(1)
    
    title = args.title or files[0].stem
    output = args.output or f"{title}.epub"
    
    pages = []
    print(f"\nОбработка {len(files)} файлов\n")
    
    for f in files:
        text = ocr_file(f, reader)
        if text:
            if args.keep_txt:
                txt = f.with_suffix(".txt")
                txt.write_text(text, encoding="utf-8")
                print(f"txt сохранён: {txt}")
            pages.append((f.stem, text))
    
    if not pages:
        print("Не удалось извлечь текст")
        sys.exit(1)
    
    print(f"\nСборка EPUB ({len(pages)} глав)...")
    build_book(pages, output, title, args.author, args.epub_lang)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSTOP")
        sys.exit(0)
