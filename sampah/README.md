# Sampah sementara

Folder ini menampung file yang sudah dipastikan tidak dipakai oleh aplikasi saat ini, tetapi belum dihapus agar bisa ditinjau dan dipulihkan.

## Kandidat yang dikarantina

| Asal | Lokasi sekarang | Alasan |
| --- | --- | --- |
| `apps/web/src/components/ui/tooltip.tsx` | `sampah/apps/web/src/components/ui/tooltip.tsx` | Tidak ada komponen `Tooltip`, `TooltipTrigger`, atau `TooltipContent` yang dipakai aplikasi. Hanya `TooltipProvider` yang membungkus seluruh layout, sehingga wrapper itu dilepas. |

Untuk memulihkan file, pindahkan kembali ke lokasi asal dan tambahkan provider hanya jika UI memakai tooltip.

## Tetap disimpan di lokasi proyek

Gallery, laporan, data, notebook, dan log lama tidak dikarantina bila masih dirujuk oleh laporan atau merekam provenance eksperimen. Contohnya gallery AI-018 sebelum review ditandai sebagai superseded, tetapi laporan dan log masih mengikatnya sebagai bukti historis. Checkpoint dan output training lokal yang diabaikan Git juga tidak diubah.

Tinjau isi folder ini sebelum menghapusnya. File di sini tidak dihapus oleh proses cleanup ini.
