document.addEventListener("DOMContentLoaded", () => {
    const gradeSelect = document.getElementById("grade-select");
    const themeSelect = document.getElementById("theme-select");
    const analyzeBtn = document.getElementById("analyze-btn");
    const resultsSection = document.getElementById("results-section");

    // UI Elements
    const btnText = analyzeBtn.querySelector(".btn-text");
    const loader = analyzeBtn.querySelector(".loader");

    // Tab Buttons
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // JSON alanları ve karşılık gelen HTML element ID'leri
    const FIELD_IDS = [
        "etkinlik",
        "baglam_temelli_soru",
        "karsilastirmali_analiz",
        "ders_plani"
    ];

    // Sınıf değiştiğinde temaları arka plandan çek ve güncelle
    gradeSelect.addEventListener("change", async () => {
        const grade = gradeSelect.value;
        try {
            const response = await fetch(`/api/themes?grade=${grade}`);
            const data = await response.json();

            themeSelect.innerHTML = "";
            data.themes.forEach(theme => {
                const option = document.createElement("option");
                option.value = theme;
                option.textContent = theme;
                themeSelect.appendChild(option);
            });
        } catch (error) {
            console.error("Temalar yüklenemedi:", error);
        }
    });

    // Sekme (Tab) Değiştirme Mantığı
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const targetId = btn.getAttribute("data-target");
            tabPanes.forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === targetId) {
                    pane.classList.add("active");
                }
            });
        });
    });

    // Analiz Et Butonu Tıklaması
    analyzeBtn.addEventListener("click", async () => {
        const grade = gradeSelect.value;
        const theme = themeSelect.value;

        // Yükleme animasyonunu başlat
        btnText.classList.add("hidden");
        loader.classList.remove("hidden");
        analyzeBtn.disabled = true;

        // Kullanıcıya bilgi ver
        const waitingMsg = "Yapay Zeka PDF'leri okuyor ve analiz ediyor... (Bu işlem 15-30 saniye sürebilir)";
        FIELD_IDS.forEach(id => {
            document.getElementById(id + "-text").textContent = waitingMsg;
        });

        // Sonuç alanını görünür yap ve ilk sekmeye geç
        resultsSection.classList.remove("hidden");
        tabBtns[0].click();

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ grade: grade, theme: theme })
            });

            const data = await response.json();

            // Gelen verileri UI'a yerleştir
            FIELD_IDS.forEach(id => {
                if (data[id]) {
                    document.getElementById(id + "-text").textContent = data[id];
                }
            });

            // İlk sekmeye odaklan
            tabBtns[0].click();

            setTimeout(() => {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);

        } catch (error) {
            alert("Veriler alınırken bir hata oluştu. Lütfen tekrar deneyin.");
            console.error(error);
        } finally {
            setTimeout(() => {
                btnText.classList.remove("hidden");
                loader.classList.add("hidden");
                analyzeBtn.disabled = false;
            }, 300);
        }
    });
});
