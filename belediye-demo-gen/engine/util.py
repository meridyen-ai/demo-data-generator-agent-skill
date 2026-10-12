"""Uretim yardimcilari: deterministik RNG, CSV yazici, Turkce isim havuzlari."""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import random

# ---------------------------------------------------------------- tarih araligi
BASLANGIC = dt.date(2019, 1, 1)
BITIS = dt.date(2026, 8, 31)
YILLAR = list(range(2019, 2027))
GUN_SAYISI = (BITIS - BASLANGIC).days + 1


def gunler(bas=None, bit=None):
    bas = bas or BASLANGIC
    bit = bit or BITIS
    d = bas
    while d <= bit:
        yield d
        d += dt.timedelta(days=1)


def aylar(bas=None, bit=None):
    bas = bas or BASLANGIC
    bit = bit or BITIS
    y, m = bas.year, bas.month
    while (y, m) <= (bit.year, bit.month):
        yield dt.date(y, m, 1)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def ay_sonu(d):
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return dt.date(y, m, 1) - dt.timedelta(days=1)


def rastgele_gun(rng, bas=None, bit=None):
    """[bas, bit] araliginda rastgele gun; aralik bosalirsa ust siniri dondurur."""
    bas = bas or BASLANGIC
    bit = bit or BITIS
    if bas >= bit:
        return bit
    return bas + dt.timedelta(days=rng.randrange((bit - bas).days + 1))


def is_gunu(d):
    return d.weekday() < 5


# ------------------------------------------------------------------ RNG yardim
def agirlikli(rng, secenekler):
    """secenekler: [(deger, agirlik), ...]"""
    toplam = sum(w for _, w in secenekler)
    x = rng.random() * toplam
    ust = 0.0
    for v, w in secenekler:
        ust += w
        if x <= ust:
            return v
    return secenekler[-1][0]


def normal_int(rng, ort, sapma, alt=None, ust=None):
    v = int(round(rng.gauss(ort, sapma)))
    if alt is not None:
        v = max(alt, v)
    if ust is not None:
        v = min(ust, v)
    return v


def para(x):
    return f"{round(float(x), 2):.2f}"


def mevsim_carpani(d, genlik=0.18, faz=0):
    """Yil icinde yumusak mevsimsellik (1.0 ortalamali)."""
    return 1.0 + genlik * math.sin(2 * math.pi * ((d.timetuple().tm_yday / 365.0) + faz))


# --------------------------------------------------------------- CSV yazicilar
class CsvYazici:
    """Tablo spesifikasyonuna gore sirali CSV yazar; eksik/fazla kolonu yakalar."""

    def __init__(self, klasor, tablo):
        self.tablo = tablo
        self.yol = os.path.join(klasor, tablo.name + ".csv")
        self._f = open(self.yol, "w", newline="", encoding="utf-8")
        self._w = csv.writer(self._f, quoting=csv.QUOTE_MINIMAL)
        self._w.writerow(tablo.colnames)
        self.n = 0

    def yaz(self, **kw):
        eksik = [c for c in self.tablo.colnames if c not in kw]
        fazla = [k for k in kw if k not in self.tablo.colnames]
        if eksik or fazla:
            raise ValueError(
                f"{self.tablo.name}: eksik={eksik} fazla={fazla}"
            )
        self._w.writerow([_hucre(kw[c]) for c in self.tablo.colnames])
        self.n += 1

    def kapat(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()


def _hucre(v):
    if v is None:
        return ""
    if v is True:
        return "t"
    if v is False:
        return "f"
    if isinstance(v, float):
        return f"{v:.2f}"
    return v


class Depo:
    """Acik CSV yazicilarini tutar, sonda hepsini kapatip satir sayilarini verir."""

    def __init__(self, klasor):
        self.klasor = klasor
        os.makedirs(klasor, exist_ok=True)
        self._acik = {}

    def w(self, tablo):
        if tablo.name not in self._acik:
            self._acik[tablo.name] = CsvYazici(self.klasor, tablo)
        return self._acik[tablo.name]

    def kapat_hepsi(self):
        sayim = {}
        for ad, w in self._acik.items():
            sayim[ad] = w.n
            w.kapat()
        self._acik.clear()
        return sayim


# ------------------------------------------------------------- isim havuzlari
ERKEK_AD = """Ahmet Mehmet Mustafa Ali Hüseyin Hasan İbrahim Osman Yusuf Ramazan
Murat Ömer Kadir Emre Serkan Burak Fatih Erhan Volkan Onur Cem Kaan Umut Barış
Selim Tolga Levent Okan Sinan Ercan Gökhan Uğur Tuncay Bülent Erdem Alper Deniz
Eren Yiğit Kerem Berk Arda Efe Mert Ozan Halil Recep İsmail Süleyman Abdullah
Zeki Necati Hakan Ferhat Turgut Adem Nuri Kemal Rıza Sedat Şener Taner Vedat
Yılmaz Coşkun Ertan Fikret Galip Haydar İlker Kürşat Metin Nihat Orhan Polat
Rahmi Sabri Şahin Tayfun Vahit Yalçın Zafer Cengiz Doğan Erol Feyyaz Gürkan
Hamdi İlhan Kenan Muhammet Nurettin Oktay Refik Salih Şükrü Tarık Ünal Yavuz""".split()

KADIN_AD = """Ayşe Fatma Emine Hatice Zeynep Elif Meryem Şerife Zehra Sultan
Hüsniye Havva Rabia Esra Merve Büşra Kübra Seda Derya Pınar Gamze Özge Tuğba
Ebru Nurcan Sevgi Selin Melis Ceren Aslı Burcu Dilek Filiz Gül Hande İrem Jale
Kader Leyla Mine Nazan Oya Perihan Rukiye Semra Tülay Ülkü Vildan Yasemin Zübeyde
Aleyna Beren Ceyda Damla Ecrin Feride Gizem Hilal İpek Kevser Lale Melike Neslihan
Nihal Özlem Pelin Reyhan Sibel Şule Tuba Ümmü Vahide Yeliz Zerrin Aysun Bahar
Cansu Dudu Eylül Fadime Gülsüm Handan Hicran İlknur Kıymet Lütfiye Mualla Nuray
Özden Pakize Rüya Sevda Şirin Tuğçe Ünzile Yıldız Zeliha Ayla Berna Cemile""".split()

SOYAD = """Yılmaz Kaya Demir Şahin Çelik Yıldız Yıldırım Öztürk Aydın Özdemir
Arslan Doğan Kılıç Aslan Çetin Kara Koç Kurt Özkan Şimşek Polat Korkmaz Çakır
Erdoğan Karadağ Aksoy Bulut Güneş Aydemir Turan Sarı Duman Şen Taş Yavuz Bozkurt
Gül Uzun Sezer Balcı Keskin Erdem Avcı Tekin Bilgin Coşkun Ünal Güler Karaca
Acar Ateş Başar Çiftçi Dinç Ekinci Fidan Gökçe Hakyemez Işık Kandemir Kaplan
Levent Mutlu Nalbant Oral Pekin Sağlam Tunç Uçar Varol Yalçın Zorlu Altın
Ay Baran Cengiz Dalkıran Elmas Fırat Genç Halıcı İnce Kalkan Küçük Mert Nazlı
Okur Öz Pala Reis Sancak Toprak Uysal Vural Yaman Zengin Adıgüzel Bayraktar
Çakmak Demirci Eroğlu Görgülü Hancı İpek Kahraman Sarıoğlu Tosun Uğurlu""".split()

FIRMA_EKI = ["İnşaat A.Ş.", "İnşaat Ltd. Şti.", "Taahhüt Ltd. Şti.",
             "Temizlik Hizmetleri A.Ş.", "Gıda San. ve Tic. Ltd. Şti.",
             "Bilişim Ltd. Şti.", "Otomotiv Ltd. Şti.", "Peyzaj Ltd. Şti.",
             "Mühendislik A.Ş.", "Enerji Ltd. Şti.", "Danışmanlık Ltd. Şti.",
             "Matbaacılık Ltd. Şti.", "Nakliyat Ltd. Şti.", "Elektrik Ltd. Şti.",
             "Güvenlik Hizmetleri A.Ş.", "Sağlık Ürünleri Ltd. Şti."]

FIRMA_KOKU = """Anadolu Marmara Boğaziçi Yıldız Kartal Öz Star Efe Nur Umut Ege
Toros Ata Bereket Şafak Mavi Altın Gümüş Zirve Kale Çınar Meltem Deniz Kaya
Aksu Bilge Doruk Erk Ferah Güven Hisar İnci Karya Lider Maya Nova Onur Pusula
Rota Sedef Tuna Ufuk Vega Yörük Zümrüt Barış Cihan Duru Elit Form Gökçe""".split()


def kisi_adi(rng, cinsiyet=None):
    c = cinsiyet or rng.choice(["E", "K"])
    ad = rng.choice(ERKEK_AD if c == "E" else KADIN_AD)
    return f"{ad} {rng.choice(SOYAD)}", c


def firma_adi(rng):
    return f"{rng.choice(FIRMA_KOKU)} {rng.choice(FIRMA_EKI)}"


def tc_no(rng):
    return str(rng.randrange(10000000000, 99999999999))


def vkn(rng):
    return str(rng.randrange(1000000000, 9999999999))


def iban(rng):
    return "TR" + "".join(str(rng.randrange(10)) for _ in range(24))


def telefon(rng):
    return f"05{rng.randrange(30, 60)}{rng.randrange(1000000, 9999999)}"
