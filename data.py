# Bu dosya Maarif Modeli tema listesini sınıflara göre barındırır.

THEMES_BY_GRADE = {
    "9": [
        "MAT.9.1. Sayılar",
        "MAT.9.2. Nicelikler ve Değişimler",
        "MAT.9.3. Algoritma ve Bilişim",
        "MAT.9.4. Geometrik Şekiller",
        "MAT.9.5. Eşlik ve Benzerlik",
        "MAT.9.6. İstatistiksel Araştırma Süreci",
        "MAT.9.7. Veriden Olasılığa"
    ],
    "10": [
        "MAT.10.1. Sayılar",
        "MAT.10.2. Nicelikler ve Değişimler",
        "MAT.10.3. Sayma, Algoritma ve Bilişim",
        "MAT.10.4. Geometrik Şekiller",
        "MAT.10.5. Analitik İnceleme",
        "MAT.10.6. İstatistiksel Araştırma Süreci",
        "MAT.10.7. Veriden Olasılığa"
    ],
    "11": [
        "MAT.11.1. Nicelikler ve Değişimler",
        "MAT.11.2. Geometrik Şekiller",
        "MAT.11.3. İstatistiksel Araştırma Süreci"
    ],
    "12": [
        "MAT.12.1. Nicelikler ve Değişimler",
        "MAT.12.2. Değişimin Matematiği",
        "MAT.12.3. Geometrik Şekiller",
        "MAT.12.4. Geometrik Cisimler",
        "MAT.12.5. Hazır Veriler Üzerinde Çalışma"
    ]
}

def get_themes_by_grade(grade):
    """Belirtilen sınıfa ait Maarif Modeli temalarını döndürür."""
    grade = str(grade)
    return THEMES_BY_GRADE.get(grade, [])
