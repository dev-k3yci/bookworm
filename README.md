# Bookworm
Image to EPUB Converter  //  Конвертер изображений в EPUB-книгу с использованием OCR

## Возможности

- Распознавание текста с изображений через EasyOCR
- Автоматическая обработка изображений (бинаризация, шумоподавление)
- Сохранение распознанного текста в отдельные TXT файлы
- Сборка EPUB-книги с титульной страницей

## Установка

```bash
git clone https://github.com/dev-k3yci/bookworm.git
cd bookworm
pip install -r requirements.txt
```

# Базовый запуск

```bash
python bookworm.py image1.png image2.jpg --title "Моя книга" --author "Автор"
