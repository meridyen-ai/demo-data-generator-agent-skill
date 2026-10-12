# -*- coding: utf-8 -*-
"""Ortak dunya durumu: parametreler, fiyat endeksi, uretilen kimlik havuzlari."""
from __future__ import annotations

import datetime as dt
import random

# yillik TUFE (%) - Turkiye gercegine yakin kurgusal degerler
ENFLASYON = {2019: 11.8, 2020: 14.6, 2021: 36.1, 2022: 64.3,
             2023: 64.8, 2024: 44.4, 2025: 31.0, 2026: 24.0}

# 2019 = 1.00 tabanli kumulatif fiyat endeksi (yil ortasi)
FIYAT_ENDEKSI = {2019: 1.00, 2020: 1.15, 2021: 1.56, 2022: 2.57,
                 2023: 4.23, 2024: 6.11, 2025: 8.00, 2026: 9.92}

# baslangic butce odenegi (TL)
BUTCE = {2019: 540_000_000, 2020: 645_000_000, 2021: 865_000_000,
         2022: 1_540_000_000, 2023: 2_700_000_000, 2024: 4_310_000_000,
         2025: 6_225_000_000, 2026: 7_950_000_000}

MAHALLELER = [
    # (ad, 2026 nufus, alan km2, segment, enlem, boylam)
    ("Bahçelievler",      42800, 0.98, "Orta",      41.00450, 28.85820),
    ("Cumhuriyet",        47600, 1.12, "Orta",      41.01180, 28.84690),
    ("Çobançeşme",        33200, 1.35, "Alt-Orta",  40.99420, 28.82160),
    ("Fevzi Çakmak",      55900, 1.24, "Orta",      41.00810, 28.83540),
    ("Hürriyet",          48300, 0.91, "Üst-Orta",  41.00120, 28.86540),
    ("Kocasinan Merkez",  62400, 1.48, "Orta",      41.01640, 28.86010),
    ("Siyavuşpaşa",       45100, 0.87, "Üst-Orta",  41.00930, 28.87220),
    ("Soğanlı",           51700, 1.06, "Alt-Orta",  40.99870, 28.87940),
    ("Şirinevler",        78300, 1.41, "Orta",      40.99310, 28.84280),
    ("Yenibosna Merkez",  92600, 2.18, "Alt-Orta",  40.99050, 28.82870),
    ("Zafer",             39400, 0.79, "Üst-Orta",  41.00560, 28.88110),
]

YAS_BANTLARI = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34",
                "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
                "65-69", "70-74", "75-79", "80+"]

# yas bandi nufus payi (Turkiye ilce ortalamasina yakin)
YAS_PAYI = [0.062, 0.066, 0.070, 0.072, 0.079, 0.082, 0.085, 0.081, 0.074,
            0.066, 0.059, 0.052, 0.044, 0.034, 0.024, 0.015, 0.015]

EGITIM = ["Okur-yazar değil", "İlkokul", "Ortaokul", "Lise", "Ön lisans",
          "Lisans", "Lisansüstü"]
EGITIM_AGIRLIK = [0.03, 0.20, 0.17, 0.31, 0.10, 0.16, 0.03]

CALISMA_DURUMU = ["Çalışıyor", "İşsiz", "Emekli", "Öğrenci", "Ev hanımı", "Çalışamaz"]

MESLEKLER = ["Tekstil işçisi", "Şoför", "Satış danışmanı", "Öğretmen", "Muhasebeci",
             "Garson", "Kuaför", "Elektrikçi", "İnşaat işçisi", "Hemşire", "Doktor",
             "Mühendis", "Güvenlik görevlisi", "Temizlik personeli", "Aşçı",
             "Terzi", "Berber", "Kasap", "Emlakçı", "Bankacı", "Avukat", "Esnaf",
             "Kurye", "Depo görevlisi", "Yazılımcı", "Grafiker", "Teknisyen",
             "Serbest meslek", "Fabrika işçisi", "Market kasiyeri"]

GELIR_BANDI = ["0-15.000 TL", "15.001-25.000 TL", "25.001-40.000 TL",
               "40.001-65.000 TL", "65.001-100.000 TL", "100.000 TL üzeri"]


class World:
    """Uretim boyunca paylasilan durum."""

    def __init__(self, seed, depo):
        self.seed = seed
        self.depo = depo
        self.rng = random.Random(seed)
        self.sayim = {}

    def r(self, ad):
        """Modul bazli deterministik alt-RNG."""
        return random.Random(self.seed * 7919 + (abs(hash(ad)) % 100000))

    # ---- fiyat endeksi -----------------------------------------------------
    def endeks(self, d):
        """Tarihe gore (aylik enterpolasyonlu) fiyat endeksi."""
        if isinstance(d, int):
            return FIYAT_ENDEKSI[d]
        y = d.year
        alt = FIYAT_ENDEKSI[y]
        ust = FIYAT_ENDEKSI.get(y + 1, alt * (1 + ENFLASYON.get(y, 25) / 100))
        t = (d.month - 1) / 12.0
        return alt + (ust - alt) * t

    # ---- nufus -------------------------------------------------------------
    def nufus(self, mahalle_id, yil):
        m = self.mahalle_ham[mahalle_id - 1]
        # 2026 tabanindan geriye dogru ~%0.55 yillik buyume
        return int(round(m[1] / (1.0055 ** (2026 - yil))))
