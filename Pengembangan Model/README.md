# 📘 Task Summarization untuk Highlight Berita

Repositori ini berisi implementasi **Automatic Text Summarization** untuk menghasilkan **highlight berita berbahasa Indonesia** menggunakan pendekatan **abstractive summarization berbasis Transformer (IndoT5)**.

Penelitian ini melakukan **fine-tuning dua model pretrained**, yaitu:
- **IndoT5-Cahya**
- **IndoT5-Wikidepia**

Kedua model tersebut **dilatih menggunakan dataset berita Tempo**, sehingga perbandingan kinerja difokuskan pada **pengaruh sumber pretraining model** terhadap kualitas ringkasan, bukan pada perbedaan dataset pelatihan.

---

## 👥 Kelompok 3
- **Ni Komang Vaniya Apriandani** (2205551019)  
- **Pande Komang Indah Triroshanti** (2205551053)  
- **Sinta Purnama Dewi** (2205551100)  

---

## 🎯 Tujuan Proyek
- Mengembangkan sistem peringkasan otomatis untuk berita Indonesia
- Melakukan fine-tuning ulang model IndoT5 menggunakan data berita Tempo
- Membandingkan kualitas ringkasan antara:
  - Model IndoT5-Cahya
  - Model IndoT5-Wikidepia
- Menganalisis pengaruh karakteristik data pretraining terhadap hasil ringkasan

---

## 🗂️ Struktur Proyek


---

## 📄 Penjelasan File

### 🔹 `scraptempo.py`
Script Python untuk **mengumpulkan data berita dari Tempo**.
- Melakukan scraping konten artikel berita
- Mengambil teks berita dan highlight
- Menghasilkan dataset mentah sebagai input pelatihan

---

### 🔹 `preprocessing_data.ipynb`
Notebook untuk **pra-pemrosesan dataset Tempo**, meliputi:
- Pembersihan teks (cleaning & normalisasi)
- Penghapusan noise dan karakter tidak relevan
- Penyesuaian format input–output sesuai skema IndoT5
- Pembagian data untuk proses pelatihan dan evaluasi

Notebook ini menjadi tahap awal sebelum proses fine-tuning model.

---

### 🔹 `5epoch_wikidepia.ipynb`
Notebook fine-tuning **IndoT5-Wikidepia** menggunakan dataset Tempo dengan:
- Jumlah epoch: **5**
- Digunakan sebagai eksperimen awal (baseline)
- Mengamati stabilitas dan arah pembelajaran model

---

### 🔹 `20epoch_wikidepia.ipynb`
Notebook fine-tuning lanjutan **IndoT5-Wikidepia** menggunakan dataset Tempo dengan:
- Jumlah epoch: **20**
- Fokus pada peningkatan kualitas ringkasan
- Evaluasi koherensi dan relevansi isi ringkasan

---

### 🔹 `20epoch_cahyaindoT5.ipynb`
Notebook fine-tuning **IndoT5-Cahya** menggunakan dataset Tempo dengan:
- Jumlah epoch: **20**
- Digunakan sebagai pembanding terhadap IndoT5-Wikidepia
- Analisis kecenderungan ringkasan akibat karakteristik pretraining Liputan6
