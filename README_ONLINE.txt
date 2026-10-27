FETCHHUB ONLINE - REAL DOWNLOAD

Ini versi ONLINE nyata, bukan simulasi.

Cara bikin ONLINE:
1. Unzip
2. docker-compose up --build -d
3. Buka http://YOUR_SERVER_IP:3000
4. Test: paste https://youtube.com/shorts/HeikLIVC8hk?si=X_EdMKEqzt_d1vUx
   Pilih Video 1080p -> Download -> file MP4 asli turun

Cek backend online:
curl http://localhost:8000/api/status
-> {"status":"online",...}

Jika backend offline di preview Meta AI itu normal karena preview statis.
Setelah deploy dengan docker-compose, status akan ONLINE dan download file asli.

Tested format:
- youtube.com/shorts/... (shorts support)
- youtube.com/watch?v=...
- youtu.be/...
- facebook.com/watch, fb.watch

Engine: yt-dlp + ffmpeg
