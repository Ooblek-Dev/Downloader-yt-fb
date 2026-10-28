IDM Online HP FIX

Bug: File video tidak tersimpan di HP
Fix: Backend support GET /api/download?url=...&format=... + blob fallback + Save to HP button + 60s revoke delay

Run: docker-compose up --build -d
Frontend: http://YOUR_IP:3000
Backend: http://YOUR_IP:8000/docs

HP Test:
1. Buka di HP Chrome
2. Add URL -> Download
3. File masuk Internal Storage/Download/
Jika gagal: tap Save to HP
