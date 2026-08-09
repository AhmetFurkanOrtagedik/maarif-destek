import os
import json
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

# Bellekte tutulacak birleştirilmiş metin havuzu
_COMBINED_CONTEXT = ""

def get_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "buraya_api_anahtarinizi_yaziniz":
        raise ValueError("API Anahtarı bulunamadı! Lütfen .env dosyasını güncelleyin.")
    return api_key

def extract_text_from_pdf(pdf_path):
    """Verilen PDF dosyasından metin çıkarır."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"  [HATA] PDF okunamadı ({pdf_path}): {e}")
    return text

def init_context():
    """'mufredatlar' klasöründeki TÜM PDF dosyalarını tarayarak
    etiketlenmiş tek bir büyük metin havuzu (context) oluşturur."""
    global _COMBINED_CONTEXT

    # Zaten okunduysa tekrar okuma
    if _COMBINED_CONTEXT:
        return

    # mufredatlar klasörünün yolu
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_folder = os.path.join(base_dir, "mufredatlar")

    if not os.path.isdir(pdf_folder):
        print(f"[UYARI] 'mufredatlar' klasörü bulunamadı: {pdf_folder}")
        return

    # Klasördeki tüm .pdf dosyalarını bul
    pdf_files = sorted([
        f for f in os.listdir(pdf_folder)
        if f.lower().endswith(".pdf")
    ])

    if not pdf_files:
        print("[UYARI] 'mufredatlar' klasöründe hiç PDF dosyası bulunamadı.")
        return

    print(f"Toplam {len(pdf_files)} adet PDF dosyası bulundu. Okunuyor...")

    all_texts = []
    for filename in pdf_files:
        filepath = os.path.join(pdf_folder, filename)
        print(f"  → {filename} okunuyor...")

        # Dosya adından etiket üret (uzantıyı kaldır, okunabilir yap)
        label = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").upper()
        text = extract_text_from_pdf(filepath)

        if text.strip():
            all_texts.append(f"--- {label} BAŞLANGIÇ ---\n{text}\n--- {label} BİTİŞ ---")
            print(f"  ✓ {filename} başarıyla okundu ({len(text)} karakter)")
        else:
            print(f"  ✗ {filename} boş veya okunamadı.")

    # Tüm metinleri birleştir
    _COMBINED_CONTEXT = "\n\n".join(all_texts)
    print(f"Metin havuzu oluşturuldu. Toplam boyut: {len(_COMBINED_CONTEXT)} karakter")

def analyze_curriculum(grade, theme):
    """Birleştirilmiş PDF metin havuzunu kullanarak Gemini API'ye analiz isteği atar."""
    try:
        api_key = get_api_key()
        init_context()

        # Stabil çalıştığı doğrulanmış model ve endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

        # Metin havuzunu token sınırına uygun şekilde kırp
        context_text = _COMBINED_CONTEXT[:900000] if _COMBINED_CONTEXT else "(Hiçbir PDF okunamadı)"

        prompt = f"""
Sen bir Lise Matematik Uzmanı ve Eğitim Teknoloğusun.
Aşağıda sana birden fazla müfredat dokümanının birleştirilmiş içeriğini veriyorum.
Bu dokümanlar arasında "Maarif Modeli (Yeni Program)" ve "2018 Müfredatı (Eski Program)" bulunmaktadır.
İçerik geliştirme ve soru üretmede ANA KAYNAKIN Maarif Modeli olacak.
2018 Müfredatını sadece karşılaştırma yaparken referans olarak kullanacaksın.

--- TÜM DOKÜMANLAR (BİRLEŞTİRİLMİŞ METİN HAVUZU) ---
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
