import os
import json
import gc
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

# ── Sabitler ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, "mufredatlar")
CACHE_FOLDER = os.path.join(BASE_DIR, "mufredatlar", "_cache")

def get_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "buraya_api_anahtarinizi_yaziniz":
        raise ValueError("API Anahtarı bulunamadı! Lütfen .env dosyasını güncelleyin.")
    return api_key

# ─────────────────────────────────────────────
# AŞAMA 1: Disk Önbelleği (Cache) Sistemi
# PDF → .txt dönüşümünü sadece BİR KERE yapar,
# sonraki her okumada hafif .txt dosyasını kullanır.
# ─────────────────────────────────────────────

def _get_cache_path(pdf_filename):
    """PDF dosya adına karşılık gelen önbellek (.txt) yolunu döndürür."""
    txt_name = os.path.splitext(pdf_filename)[0] + ".txt"
    return os.path.join(CACHE_FOLDER, txt_name)

def _is_cache_fresh(pdf_path, cache_path):
    """Önbellek dosyası PDF'den daha yeni mi kontrol eder."""
    if not os.path.exists(cache_path):
        return False
    return os.path.getmtime(cache_path) >= os.path.getmtime(pdf_path)

def _extract_and_cache(pdf_path, cache_path):
    """PDF'i sayfa sayfa okuyup doğrudan diske yazar. RAM'de birikim yapmaz."""
    os.makedirs(CACHE_FOLDER, exist_ok=True)
    filename = os.path.basename(pdf_path)
    label = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").upper()

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"  → {filename}: {total_pages} sayfa işleniyor...")

        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(f"--- {label} BAŞLANGIÇ ---\n")
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    f.write(text + "\n")
                # Her 20 sayfada bir belleği temizle
                if (i + 1) % 20 == 0:
                    gc.collect()
            f.write(f"--- {label} BİTİŞ ---\n")

        # PDF reader'ı bellekten temizle
        del reader
        gc.collect()

        size_kb = os.path.getsize(cache_path) / 1024
        print(f"  ✓ {filename} önbelleğe yazıldı ({size_kb:.0f} KB)")
        return True

    except Exception as e:
        print(f"  ✗ {filename} okunamadı: {e}")
        return False

def ensure_cache():
    """Tüm PDF'lerin disk önbelleğini hazırlar (gerekiyorsa)."""
    if not os.path.isdir(PDF_FOLDER):
        print(f"[UYARI] 'mufredatlar' klasörü bulunamadı: {PDF_FOLDER}")
        return

    pdf_files = sorted([f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")])
    if not pdf_files:
        print("[UYARI] 'mufredatlar' klasöründe hiç PDF dosyası bulunamadı.")
        return

    needs_update = False
    for filename in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, filename)
        cache_path = _get_cache_path(filename)
        if not _is_cache_fresh(pdf_path, cache_path):
            needs_update = True
            break

    if not needs_update:
        print("Önbellek güncel, PDF tekrar okunmayacak.")
        return

    print(f"{len(pdf_files)} PDF dosyası önbelleğe alınıyor (tek seferlik)...")
    for filename in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, filename)
        cache_path = _get_cache_path(filename)
        if not _is_cache_fresh(pdf_path, cache_path):
            _extract_and_cache(pdf_path, cache_path)

    gc.collect()
    print("Önbellekleme tamamlandı.")

# ─────────────────────────────────────────────
# AŞAMA 2: Akıllı Bağlam Filtreleme
# Tüm metni RAM'e yığmak yerine, sadece
# seçilen sınıf+temaya ilişkin bölümleri çeker.
# ─────────────────────────────────────────────

def _load_relevant_context(grade, theme, max_chars=120000):
    """Önbellek dosyalarından sadece ilgili bölümleri çekerek küçük bir bağlam oluşturur."""
    if not os.path.isdir(CACHE_FOLDER):
        return "(Önbellek klasörü bulunamadı. Lütfen sunucuyu yeniden başlatın.)"

    cache_files = sorted([f for f in os.listdir(CACHE_FOLDER) if f.endswith(".txt")])
    if not cache_files:
        return "(Önbellek dosyası bulunamadı.)"

    # Arama anahtar kelimeleri
    grade_str = str(grade)
    keywords = [
        f"MAT.{grade_str}",
        f"{grade_str}. sınıf",
        f"{grade_str}.sınıf",
        theme,
    ]
    # Tema kodundan alt anahtar kelimeler çıkar (örn: "MAT.9.1. Sayılar" → ["sayılar", "mat.9.1"])
    theme_words = [w.strip(".").lower() for w in theme.split() if len(w) > 2]
    keywords.extend(theme_words)

    relevant_chunks = []
    total_chars = 0

    for cache_file in cache_files:
        cache_path = os.path.join(CACHE_FOLDER, cache_file)
        try:
            # Dosyayı satır satır oku (tamamını RAM'e yüklemeden)
            with open(cache_path, "r", encoding="utf-8") as f:
                current_chunk = []
                chunk_relevant = False

                for line in f:
                    current_chunk.append(line)

                    # Her 30 satırda bir blok değerlendir
                    if len(current_chunk) >= 30:
                        block_text = "".join(current_chunk)
                        block_lower = block_text.lower()

                        # Anahtar kelimelerden herhangi biri geçiyorsa bloğu al
                        if any(kw.lower() in block_lower for kw in keywords):
                            relevant_chunks.append(block_text)
                            total_chars += len(block_text)

                        current_chunk = []

                        # Karakter limitine ulaştıysak dur
                        if total_chars >= max_chars:
                            break

                # Kalan satırları da kontrol et
                if current_chunk and total_chars < max_chars:
                    block_text = "".join(current_chunk)
                    block_lower = block_text.lower()
                    if any(kw.lower() in block_lower for kw in keywords):
                        relevant_chunks.append(block_text)
                        total_chars += len(block_text)

        except Exception as e:
            print(f"  [HATA] Önbellek okunamadı ({cache_file}): {e}")

    if not relevant_chunks:
        # Hiç eşleşme bulunamadıysa, her dosyanın başından bir parça al
        for cache_file in cache_files:
            cache_path = os.path.join(CACHE_FOLDER, cache_file)
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    head = f.read(max_chars // len(cache_files))
                    relevant_chunks.append(head)
            except Exception:
                pass

    context = "\n\n".join(relevant_chunks)
    print(f"Bağlam hazırlandı: {len(context)} karakter ({len(relevant_chunks)} blok)")
    return context[:max_chars]

# ─────────────────────────────────────────────
# AŞAMA 3: Gemini API İsteği
# ─────────────────────────────────────────────

def analyze_curriculum(grade, theme):
    """Filtrelenmiş bağlamı kullanarak Gemini API'ye analiz isteği atar."""
    try:
        api_key = get_api_key()

        # Önbelleği hazırla (ilk çağrıda PDF→TXT dönüşümü yapılır)
        ensure_cache()

        # Sadece ilgili bölümleri çek (tüm metin yerine ~120K karakter)
        context_text = _load_relevant_context(grade, theme)

        # Stabil çalıştığı doğrulanmış model ve endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

        prompt = f"""
Sen bir Lise Matematik Uzmanı ve Eğitim Teknoloğusun.
Aşağıda sana müfredat dokümanlarından seçilen sınıf ve temaya ilişkin bölümleri veriyorum.
Bu bölümler arasında "Maarif Modeli (Yeni Program)" ve "2018 Müfredatı (Eski Program)" içerikleri bulunmaktadır.
İçerik geliştirme ve soru üretmede ANA KAYNAKIN Maarif Modeli olacak.
2018 Müfredatını sadece karşılaştırma yaparken referans olarak kullanacaksın.

--- İLGİLİ MÜFREDAT BÖLÜMLERİ ---
{context_text}

BİR ÖĞRETMEN SENDEN YARDIM İSTİYOR.
Seçtiği Sınıf: {grade}. Sınıf
Seçtiği Tema: {theme}

GÖREV: Öğretmenler için Maarif Modeli'ne uygun içerikler üret ve 2018 müfredatı ile karşılaştırmalı analiz yap.

KURALLAR:
1. ETKİNLİK TAVSİYESİ: Maarif Modeli'ne uygun, disiplinler arası, öğrenciyi meraklandıran, sınıfta uygulanabilir detaylı bir etkinlik tasarla. Süre, materyal ve uygulama adımlarını belirt.
2. BAĞLAM TEMELLİ SORU: Soruyu doğrudan denklem çözdürme üzerine değil; bir olay, problem durumu veya veri analizi senaryosu ile kurgula. Maarif Modeli'nin "beceri temelli" yapısına tam sadık kal.
3. ÖRNEK DERS PLANI: Maarif Modeli'ndeki öğrenme döngüsüne uygun planla: (1) Merak, (2) Keşfet, (3) Açıkla, (4) Derinleştir, (5) Değerlendir aşamalarını içersin. Her aşamada süre ve etkinlik belirt.
4. KARŞILAŞTIRMALI ANALİZ (KRİTİK): 2018 programını içerik üretmek için KULLANMA, ancak bu alanda Maarif Modeli ile 2018 programını analitik olarak kıyasla. 2018'de işlem yoğunluğu veya konu sırası nasıldı, Maarif'te kavramsal derinlik nasıl değişti? Bu karşılaştırmayı yaparken 2018'i sadece "geçmiş bir referans" olarak kullan.

ÇIKTI: Sadece aşağıdaki JSON formatında cevap ver. Başka açıklama veya markdown ekleme:
{{
    "etkinlik": "Maarif Modeli'ne uygun, disiplinler arası detaylı etkinlik önerisi.",
    "baglam_temelli_soru": "Bir olay, problem durumu veya veri analizi senaryosu ile kurgulanmış beceri temelli soru.",
    "ders_plani": "Merak-Keşfet-Açıkla-Derinleştir-Değerlendir döngüsüne uygun profesyonel ders planı.",
    "karsilastirmali_analiz": "2018 müfredatı ile Maarif Modeli arasındaki vizyon kayması, işlem yoğunluğu farkı ve kavramsal derinlik değişimlerinin analizi."
}}
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        headers = {
            "Content-Type": "application/json"
        }

        print(f"Yapay zeka analiz ediyor: {grade}. Sınıf - {theme}...")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response_data = response.json()

        if response.status_code != 200:
            print("API Hata Yanıtı:", response_data)
            raise Exception(f"API HTTP {response.status_code}: {response_data.get('error', {}).get('message', 'Bilinmeyen hata')}")

        # Yanıtı parse et
        text_response = response_data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text_response.replace("```json", "").replace("```", "").strip())
        return result

    except Exception as e:
        print("Yapay Zeka Analiz Hatası:", e)
        return {
            "etkinlik": "Analiz sırasında bir hata oluştu. İnternet bağlantınızı kontrol edin.",
            "baglam_temelli_soru": "Hata: " + str(e),
            "karsilastirmali_analiz": "Yapay zeka yanıtı alınamadı.",
            "ders_plani": "Sunucu tarafındaki konsolu inceleyerek hatanın detayını görebilirsiniz."
        }
