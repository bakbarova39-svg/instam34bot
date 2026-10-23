FROM python:3.11-slim

# Tizim uchun ffmpeg va kerakli utilitalarni o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini ko'chirish
COPY . .

# downloads papkasini yaratish
RUN mkdir -p downloads

# Portni ochish (Cloud hostinglar uchun)
EXPOSE 8080
ENV PORT=8080

# Botni ishga tushirish
CMD ["python", "main.py"]
