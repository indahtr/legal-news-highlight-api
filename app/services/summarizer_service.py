import re
from transformers import pipeline

MODEL_PATH = "models/finetuned_wikidepia"
MAX_INPUT_TOKENS = 512  

summarizer = pipeline(
    "summarization",
    model=MODEL_PATH,
    tokenizer=MODEL_PATH
)

tokenizer = summarizer.tokenizer

#   FUNGSI-FUNGSI PREPROCESS
def strip_tempo_prefix(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # 1) Hapus baris mandiri "TEMPO.CO , Kota -"
    text = re.sub(r'(?i)^\s*TEMPO\.CO\s*,?\s*[A-Za-z. ]+?-+\s*$\n?', '', text, flags=re.MULTILINE)
    # 2) Hapus prefix di awal paragraf:
    text = re.sub(r'(?i)^\s*TEMPO\.CO\s*,?\s*[A-Za-z. ]+?-+\s*', '', text).strip()
    return text

def remove_info_prefix(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Hapus awalan seperti "INFO NASIONAL -", "INFO BISNIS -"
    return re.sub(r'^(INFO\s+[A-Z]+\s*-\s*)', '', text, flags=re.IGNORECASE).strip()

def remove_leading_dash(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Hapus "-" atau "—" di awal kalimat
    return re.sub(r'^[\-\—]\s*', '', text).strip()

def fix_first_word_glue_and_caps(text: str) -> str:
    if not isinstance(text, str):
        return ""
    
    # 1) Fix kasus huruf pertama terpisah: "A DA" → "Ada"
    text = re.sub(r'^([A-Za-z])\s+([a-z]+)', lambda m: m.group(1) + m.group(2), text)

    # 2) Fix kasus Tempo: "L EGALISASI" → "Legalisasi"
    text = re.sub(r'^([A-Z])\s+([A-Z][a-zA-Z]+)', lambda m: m.group(1) + m.group(2).lower(), text)

    # 3) Kapitalisasi awal kalimat
    return text[:1].upper() + text[1:] if text else text

ACRONYMS = {
    "KPK", "PT", "TNI", "POLRI", "DPR", "RI", "KPU", "BPK", "BNN","MA", "MK", "LAN", "LPSK", "KejarI", "Kejagung"
}

def normalize_first_words(text: str) -> str:
    if not isinstance(text, str):
        return ""
    
    text = text.strip()
    parts = text.split(" ", 2)

    if len(parts) == 1:
        w = parts[0]
        if w.isupper() and w not in ACRONYMS and len(w) > 3:
            return w.capitalize()
        return text

    w1 = parts[0]
    if w1.isupper() and w1 not in ACRONYMS and len(w1) > 3:
        parts[0] = w1.capitalize()

    if len(parts) > 1:
        w2 = parts[1]
        if w1.isupper() and w2.isupper():
            if w1 not in ACRONYMS:
                parts[0] = w1.capitalize()
            if w2 not in ACRONYMS:
                parts[1] = w2.capitalize()

    return " ".join(parts)

def drop_stray_repeated_letter(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Hapus huruf tunggal nyasar sebelum kata: "Polisi i mengatakan" → "Polisi mengatakan"
    return re.sub(r'\b([a-zA-Z])\s+(?=[a-z])', '', text)

def remove_tempo_boilerplate(text: str) -> str:
    if not isinstance(text, str):
        return ""
    patterns = [
        r'Baca juga:.*$',
        r'Ikuti berita.*$',
        r'Dapatkan update.*$',
        r'Klik untuk.*$',
        r'\bTEMPO\.CO\b\s*$'
    ]
    for p in patterns:
        text = re.sub(p, '', text, flags=re.IGNORECASE | re.MULTILINE)
    return text.strip()

def fix_punct_spacing_strict(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Hilangkan spasi ganda
    text = re.sub(r'\s+', ' ', text)
    # Rapikan spasi sebelum tanda baca
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    return text.strip()

def rapikan_singkatan(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Hapus spasi setelah "(" dan sebelum ")"
    return re.sub(r'\(\s*([A-Za-z0-9]+)\s*\)', r'(\1)', text)

def ensure_period(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if re.search(r'[.!?]$', text):
        return text
    text = re.sub(r'[\-:;,]+$', '', text).strip()
    return text + '.'

def fix_spacing(text: str) -> str:
    if not isinstance(text, str):
        return ""
    
    # Hilangkan spasi sebelum tanda baca umum
    text = re.sub(r'\s+([,.!?):])', r'\1', text)
    # Hilangkan spasi sebelum tanda kutip penutup
    text = re.sub(r'\s+(["”])', r'\1', text)
    # Pastikan ada spasi setelah kutip kalau diikuti huruf
    text = re.sub(r'(["”])(?=[A-Za-z])', r'\1 ', text)
    # Rapikan spasi ganda
    text = re.sub(r'\s{2,}', ' ', text)

    return text.strip()

def preprocess_input_text(content: str) -> str:
    text = content if isinstance(content, str) else ""
    text = strip_tempo_prefix(text)
    text = remove_info_prefix(text)
    text = remove_leading_dash(text)
    text = fix_first_word_glue_and_caps(text)
    text = normalize_first_words(text)
    text = drop_stray_repeated_letter(text)
    text = remove_tempo_boilerplate(text)
    text = fix_punct_spacing_strict(text)
    text = rapikan_singkatan(text)
    text = fix_spacing(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def truncate_to_max_tokens(text: str, max_tokens: int = MAX_INPUT_TOKENS) -> str:
    """
    Memotong teks supaya tidak lebih dari max_tokens
    """
    if not text:
        return text
    encoded = tokenizer.encode(text, truncation=True, max_length=max_tokens)
    return tokenizer.decode(encoded, skip_special_tokens=True)

def generate_highlight_from_text(
    content: str,
    max_length: int = 75,
    min_length: int = 30,
    no_repeat_ngram_size: int = 2
) -> str:

    # 1. Preprocess sesuai pola training
    text = preprocess_input_text(content)
    if not text:
        return ""

    # 2. Batasi panjang input
    text = truncate_to_max_tokens(text, MAX_INPUT_TOKENS)

    # 3. Panggil model IndoT5 via pipeline
    result = summarizer(
        text,
        max_new_tokens=max_length,
        min_length=min_length,
        no_repeat_ngram_size=no_repeat_ngram_size,
        do_sample=False,
    )

    summary_text = result[0]["summary_text"].strip()

    # 5. Filter kalimat 
    sentences = summary_text.split(".")
    clean_sentences = []

    for s in sentences:
        s = s.strip()
        if not s:
            continue

        words = s.split()

        # 1. Hapus kalimat sangat pendek (< 3 kata)
        if len(words) < 3:
            continue

        # 2. Hapus kalimat jika kata terakhir terlalu pendek
        if len(words[-1]) <= 2:
            continue

        clean_sentences.append(s)

    # Jika setelah filtering semua hilang, pakai versi asli
    if not clean_sentences:
        highlight = summary_text
    else:
        highlight = ". ".join(clean_sentences)
        highlight = ensure_period(highlight)

    # Rapikan lagi spasi & tanda baca di highlight akhir
    highlight = fix_punct_spacing_strict(highlight)
    highlight = fix_spacing(highlight)

    return highlight
