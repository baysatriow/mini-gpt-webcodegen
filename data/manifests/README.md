# Source manifests

Satu manifest per source/config/limit memuat revision, source URL, attribution, license, sampling method, row count, byte count, SHA-256, dan storage sebelum/sesudah. Hanya `status: complete` dengan hash sesuai file raw yang boleh digunakan pipeline.

File `.partial` dan manifest failed tidak masuk training. CLI memverifikasi checksum ketika memakai ulang download sehingga tidak mengunduh subset selesai dua kali.
