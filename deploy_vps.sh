#!/bin/bash
# VPS (Ubuntu/Debian) da botni 24/7 systemd xizmati sifatida ishga tushirish skripti

set -e

echo "=========================================================="
echo "      Telegram Bot 24/7 VPS O'rnatish Skripti"
echo "=========================================================="

# Kerakli tizim paketlarini yangilash va o'rnatish
echo "[1/4] Tizim paketlari (Python, FFmpeg) tekshirilmoqda..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv ffmpeg

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
echo "Loyiha manzili: $PROJECT_DIR"

# Virtual muhit (venv) yaratish
echo "[2/4] Virtual muhit sozlanmoqda..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Kutubxonalarni o'rnatish
echo "[3/4] Python kutubxonalari o'rnatilmoqda..."
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# downloads papkasi
mkdir -p "$PROJECT_DIR/downloads"

# Systemd servisini yaratish
echo "[4/4] 24/7 avtomatik systemd servisi yaratilmoqda..."
SERVICE_PATH="/etc/systemd/system/telegrambot.service"

sudo bash -c "cat > $SERVICE_PATH" <<EOF
[Unit]
Description=Telegram 34 Bot 24/7 Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/main.py
Restart=always
RestartSec=5
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

# Servisni faollashtirish va ishga tushirish
sudo systemctl daemon-reload
sudo systemctl enable telegrambot
sudo systemctl restart telegrambot

echo "=========================================================="
echo "✅ BOT MUVAFFAQIYATLI 24/7 ISHGA TUSHIRILDI!"
echo "Kompyuteringizni o'chirib qo'ysangiz ham serverda to'xtovsiz ishlaydi."
echo ""
echo "Foydali buyruqlar:"
echo "• Holatni ko'rish:    sudo systemctl status telegrambot"
echo "• Loglarni kuzatish:  sudo journalctl -u telegrambot -f"
echo "• Qayta yuklash:      sudo systemctl restart telegrambot"
echo "• To'xtatish:         sudo systemctl stop telegrambot"
echo "=========================================================="
