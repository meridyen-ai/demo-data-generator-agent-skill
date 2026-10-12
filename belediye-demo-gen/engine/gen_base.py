# -*- coding: utf-8 -*-
"""Referans / kurulus verileri: ilce, mahalle, sokak, mudurluk, tesis, tedarikci."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U
from .world import (MAHALLELER, BUTCE, ENFLASYON, FIYAT_ENDEKSI)

SOKAK_ADI_KOK = """Gül Menekşe Lale Papatya Karanfil Zambak Nergis Sümbül Yasemin
Manolya Ihlamur Çınar Akasya Çam Kavak Söğüt Ceviz Zeytin Palmiye Defne Fidan
Barış Huzur Sevgi Umut Şafak Güneş Yıldız Ay Deniz Dalga Rüzgar Bulut Yağmur
Bahar Yaz Sonbahar Kış Cumhuriyet Zafer İstiklal Hürriyet Adalet Birlik Kardeşlik
Dostluk Emek Sanayi Ticaret Okul Hastane Cami Pazar Çeşme Kuyu Değirmen Fırın
Marmara Ege Akdeniz Karadeniz Toros Ağrı Erciyes Uludağ Kaz Bolu Sakarya Meriç
Tuna Fırat Dicle Kızılırmak Yeşilırmak Aras Ceyhan Seyhan Göksu Aksu Filiz
Nilüfer Şebnem Çiğdem Reyhan Fesleğen Adaçayı Kekik Lavanta Ada Kale Han Konak
Bağ Bahçe Bostan Meydan Köprü Liman Yalı Tepe Yamaç Vadi Ova Kaynak Pınar""".split()

SOKAK_TURU = [("Sokak", 78), ("Cadde", 14), ("Bulvar", 3), ("Çıkmaz", 5)]

MUDURLUKLER = [
    # (ad, baskan yardimciligi, hizmet grubu, norm kadro)
    ("Yazı İşleri Müdürlüğü", "Başkan Yardımcılığı - İdari", "Destek hizmetleri", 34),
    ("İnsan Kaynakları ve Eğitim Müdürlüğü", "Başkan Yardımcılığı - İdari", "Destek hizmetleri", 41),
    ("Mali Hizmetler Müdürlüğü", "Başkan Yardımcılığı - Mali", "Mali hizmetler", 96),
    ("Strateji Geliştirme Müdürlüğü", "Başkan Yardımcılığı - Mali", "Mali hizmetler", 22),
    ("Destek Hizmetleri Müdürlüğü", "Başkan Yardımcılığı - Mali", "Destek hizmetleri", 78),
    ("İşletme ve İştirakler Müdürlüğü", "Başkan Yardımcılığı - Mali", "Mali hizmetler", 29),
    ("Emlak ve İstimlak Müdürlüğü", "Başkan Yardımcılığı - Mali", "Mali hizmetler", 44),
    ("Fen İşleri Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 168),
    ("İmar ve Şehircilik Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 87),
    ("Plan ve Proje Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 33),
    ("Yapı Kontrol Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 46),
    ("Kentsel Tasarım Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 25),
    ("Kentsel Dönüşüm ve Afet İşleri Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 38),
    ("Etüd Proje Müdürlüğü", "Başkan Yardımcılığı - Teknik", "Teknik hizmetler", 19),
    ("Temizlik İşleri Müdürlüğü", "Başkan Yardımcılığı - Kentsel", "Kentsel hizmetler", 214),
    ("Park ve Bahçeler Müdürlüğü", "Başkan Yardımcılığı - Kentsel", "Kentsel hizmetler", 152),
    ("Zabıta Müdürlüğü", "Başkan Yardımcılığı - Kentsel", "Denetim", 178),
    ("Ruhsat ve Denetim Müdürlüğü", "Başkan Yardımcılığı - Kentsel", "Denetim", 43),
    ("Ulaşım Hizmetleri Müdürlüğü", "Başkan Yardımcılığı - Kentsel", "Kentsel hizmetler", 36),
    ("Veteriner İşleri Müdürlüğü", "Başkan Yardımcılığı - Kentsel", "Kentsel hizmetler", 31),
    ("Sosyal Yardım İşleri Müdürlüğü", "Başkan Yardımcılığı - Sosyal", "Sosyal hizmetler", 67),
    ("Kültür ve Sosyal İşler Müdürlüğü", "Başkan Yardımcılığı - Sosyal", "Sosyal hizmetler", 94),
    ("Sağlık İşleri Müdürlüğü", "Başkan Yardımcılığı - Sosyal", "Sosyal hizmetler", 58),
    ("Kadın ve Aile Hizmetleri Müdürlüğü", "Başkan Yardımcılığı - Sosyal", "Sosyal hizmetler", 27),
    ("Gençlik ve Spor Hizmetleri Müdürlüğü", "Başkan Yardımcılığı - Sosyal", "Sosyal hizmetler", 49),
    ("Muhtarlık İşleri Müdürlüğü", "Başkan Yardımcılığı - İdari", "Destek hizmetleri", 14),
    ("Basın Yayın ve Halkla İlişkiler Müdürlüğü", "Başkan Yardımcılığı - İdari", "Destek hizmetleri", 52),
    ("Bilgi İşlem Müdürlüğü", "Başkan Yardımcılığı - İdari", "Destek hizmetleri", 31),
    ("Hukuk İşleri Müdürlüğü", "Başkan Yardımcılığı - İdari", "Denetim", 18),
    ("Teftiş Kurulu Müdürlüğü", "Başkan Yardımcılığı - İdari", "Denetim", 11),
]

UNVANLAR = [
    # (unvan, hizmet sinifi, istihdam turu, derece_min, derece_max, endeks)
    ("Müdür", "Genel İdare Hizmetleri", "Memur", 1, 3, 4.10),
    ("Müdür Yardımcısı", "Genel İdare Hizmetleri", "Memur", 2, 5, 3.35),
    ("Şef", "Genel İdare Hizmetleri", "Memur", 3, 7, 2.60),
    ("Uzman", "Genel İdare Hizmetleri", "Memur", 3, 8, 2.45),
    ("Memur", "Genel İdare Hizmetleri", "Memur", 5, 12, 1.80),
    ("Veri Hazırlama ve Kontrol İşletmeni", "Genel İdare Hizmetleri", "Memur", 6, 12, 1.72),
    ("Mali Hizmetler Uzmanı", "Genel İdare Hizmetleri", "Memur", 2, 7, 2.75),
    ("Zabıta Amiri", "Genel İdare Hizmetleri", "Memur", 2, 6, 2.85),
    ("Zabıta Komiseri", "Genel İdare Hizmetleri", "Memur", 4, 8, 2.30),
    ("Zabıta Memuru", "Genel İdare Hizmetleri", "Memur", 6, 12, 1.85),
    ("Mimar", "Teknik Hizmetler", "Memur", 1, 6, 3.05),
    ("İnşaat Mühendisi", "Teknik Hizmetler", "Memur", 1, 6, 3.05),
    ("Makine Mühendisi", "Teknik Hizmetler", "Memur", 2, 7, 2.95),
    ("Harita Mühendisi", "Teknik Hizmetler", "Memur", 2, 7, 2.95),
    ("Çevre Mühendisi", "Teknik Hizmetler", "Memur", 3, 8, 2.80),
    ("Bilgisayar Mühendisi", "Teknik Hizmetler", "Sözleşmeli personel", 2, 7, 3.20),
    ("Peyzaj Mimarı", "Teknik Hizmetler", "Sözleşmeli personel", 3, 8, 2.70),
    ("Şehir Plancısı", "Teknik Hizmetler", "Memur", 2, 7, 2.98),
    ("Tekniker", "Teknik Hizmetler", "Memur", 5, 10, 2.05),
    ("Teknisyen", "Teknik Hizmetler", "Sürekli işçi", 7, 13, 1.72),
    ("Doktor", "Sağlık Hizmetleri", "Sözleşmeli personel", 1, 5, 4.35),
    ("Diş Hekimi", "Sağlık Hizmetleri", "Sözleşmeli personel", 1, 5, 4.05),
    ("Veteriner Hekim", "Sağlık Hizmetleri", "Sözleşmeli personel", 2, 6, 3.35),
    ("Hemşire", "Sağlık Hizmetleri", "Sözleşmeli personel", 4, 9, 2.35),
    ("Psikolog", "Sağlık Hizmetleri", "Sözleşmeli personel", 3, 8, 2.60),
    ("Sosyal Çalışmacı", "Sağlık Hizmetleri", "Sözleşmeli personel", 3, 8, 2.50),
    ("Diyetisyen", "Sağlık Hizmetleri", "Sözleşmeli personel", 4, 9, 2.30),
    ("Avukat", "Avukatlık Hizmetleri", "Memur", 1, 6, 3.45),
    ("Şoför", "Yardımcı Hizmetler", "Sürekli işçi", 8, 13, 1.55),
    ("Temizlik Personeli", "Yardımcı Hizmetler", "Şirket personeli", 10, 15, 1.00),
    ("Park Bahçe Personeli", "Yardımcı Hizmetler", "Şirket personeli", 10, 15, 1.02),
    ("Güvenlik Görevlisi", "Yardımcı Hizmetler", "Şirket personeli", 10, 15, 1.08),
    ("Büro Personeli", "Yardımcı Hizmetler", "Şirket personeli", 9, 14, 1.12),
    ("Çağrı Merkezi Personeli", "Yardımcı Hizmetler", "Şirket personeli", 9, 14, 1.10),
    ("Cenaze Hizmetleri Personeli", "Yardımcı Hizmetler", "Şirket personeli", 10, 15, 1.06),
    ("Kütüphane Görevlisi", "Yardımcı Hizmetler", "Şirket personeli", 9, 14, 1.09),
    ("Antrenör", "Yardımcı Hizmetler", "Şirket personeli", 8, 13, 1.25),
    ("Eğitmen", "Yardımcı Hizmetler", "Şirket personeli", 8, 13, 1.22),
    ("Aşçı", "Yardımcı Hizmetler", "Şirket personeli", 9, 14, 1.18),
    ("İş Makinesi Operatörü", "Yardımcı Hizmetler", "Sürekli işçi", 8, 13, 1.62),
]

FONKSIYONEL = [
    ("01", "Genel kamu hizmetleri", [("01.1", "Yasama ve yürütme organları"),
                                     ("01.3", "Genel hizmetler"),
                                     ("01.6", "Genel karakterli diğer hizmetler")]),
    ("03", "Kamu düzeni ve güvenlik hizmetleri", [("03.2", "Zabıta hizmetleri"),
                                                   ("03.6", "Diğer kamu düzeni hizmetleri")]),
    ("04", "Ekonomik işler ve hizmetler", [("04.5", "Ulaştırma hizmetleri"),
                                            ("04.7", "Diğer endüstriler"),
                                            ("04.9", "Sınıflandırmaya girmeyen ekonomik işler")]),
    ("05", "Çevre koruma hizmetleri", [("05.1", "Atık yönetimi hizmetleri"),
                                        ("05.2", "Atık su yönetimi"),
                                        ("05.6", "Diğer çevre koruma hizmetleri")]),
    ("06", "İskan ve toplum refahı hizmetleri", [("06.1", "İskan işleri ve hizmetleri"),
                                                  ("06.2", "Toplum refahı hizmetleri"),
                                                  ("06.4", "Sokak aydınlatma hizmetleri")]),
    ("07", "Sağlık hizmetleri", [("07.2", "Ayakta yürütülen tedavi hizmetleri"),
                                  ("07.4", "Halk sağlığı hizmetleri")]),
    ("08", "Dinlenme, kültür ve din hizmetleri", [("08.1", "Dinlenme ve spor hizmetleri"),
                                                   ("08.2", "Kültür hizmetleri"),
                                                   ("08.3", "Yayın ve yayım hizmetleri")]),
    ("09", "Eğitim hizmetleri", [("09.8", "Sınıflandırmaya girmeyen eğitim hizmetleri")]),
    ("10", "Sosyal güvenlik ve sosyal yardım hizmetleri", [("10.4", "Aile ve çocuk yardım hizmetleri"),
                                                            ("10.7", "Sosyal güvenliği bulunmayanlara sağlanan hizmetler"),
                                                            ("10.9", "Sınıflandırmaya girmeyen sosyal yardım hizmetleri")]),
]

EKONOMIK_GIDER = [
    ("01", "Personel giderleri", [("01.1", "Memurlar"), ("01.2", "Sözleşmeli personel"),
                                   ("01.3", "İşçiler"), ("01.5", "Diğer personel")]),
    ("02", "Sosyal güvenlik kurumlarına devlet primi giderleri", [("02.1", "Memurlar"), ("02.3", "İşçiler")]),
    ("03", "Mal ve hizmet alım giderleri", [("03.2", "Tüketime yönelik mal ve malzeme alımları"),
                                             ("03.3", "Yolluklar"),
                                             ("03.5", "Hizmet alımları"),
                                             ("03.6", "Temsil ve tanıtma giderleri"),
                                             ("03.7", "Menkul mal, gayrimaddi hak alım, bakım ve onarım"),
                                             ("03.8", "Gayrimenkul mal bakım ve onarım giderleri")]),
    ("04", "Faiz giderleri", [("04.2", "Diğer iç borç faiz giderleri")]),
    ("05", "Cari transferler", [("05.1", "Görev zararları"), ("05.3", "Kar amacı gütmeyen kuruluşlara transferler"),
                                 ("05.4", "Hane halkına yapılan transferler"), ("05.8", "Gelirlerden ayrılan paylar")]),
    ("06", "Sermaye giderleri", [("06.1", "Mamul mal alımları"), ("06.5", "Gayrimenkul sermaye üretim giderleri"),
                                  ("06.7", "Gayrimenkul büyük onarım giderleri")]),
    ("07", "Sermaye transferleri", [("07.1", "Yurtiçi sermaye transferleri")]),
    ("09", "Yedek ödenekler", [("09.6", "Yedek ödenek")]),
]

EKONOMIK_GELIR = [
    ("01", "Vergi gelirleri", [("01.2", "Mülkiyet üzerinden alınan vergiler"),
                                ("01.3", "Dahilde alınan mal ve hizmet vergileri"),
                                ("01.9", "Başka yerde sınıflandırılmayan vergiler")]),
    ("03", "Teşebbüs ve mülkiyet gelirleri", [("03.1", "Mal ve hizmet satış gelirleri"),
                                               ("03.6", "Kira gelirleri"),
                                               ("03.9", "Diğer teşebbüs ve mülkiyet gelirleri")]),
    ("04", "Alınan bağış ve yardımlar ile özel gelirler", [("04.2", "Merkezi yönetim bütçesine dahil idarelerden alınan bağış"),
                                                            ("04.5", "Proje yardımları")]),
    ("05", "Diğer gelirler", [("05.1", "Faiz gelirleri"),
                               ("05.2", "Kişi ve kurumlardan alınan paylar"),
                               ("05.3", "Para cezaları"),
                               ("05.9", "Diğer çeşitli gelirler")]),
    ("06", "Sermaye gelirleri", [("06.1", "Taşınmaz satış gelirleri"), ("06.2", "Taşınır satış gelirleri")]),
]

TESIS_SABLON = [
    ("Belediye Ana Hizmet Binası", "Hizmet binası", 14800, 1997, 1200, 640),
    ("Ek Hizmet Binası", "Hizmet binası", 4200, 2011, 400, 180),
    ("Yenibosna Hizmet Birimi", "Hizmet binası", 1800, 2014, 150, 62),
    ("Şirinevler Hizmet Birimi", "Hizmet binası", 1450, 2016, 120, 48),
    ("Bahçelievler Kültür Merkezi", "Kültür merkezi", 6200, 2009, 850, 44),
    ("Yenibosna Kültür ve Sanat Merkezi", "Kültür merkezi", 4900, 2015, 600, 33),
    ("Soğanlı Kültür Merkezi", "Kültür merkezi", 2800, 2018, 380, 21),
    ("Zafer Sanat Akademisi", "Kültür merkezi", 2100, 2021, 260, 18),
    ("Kapalı Yüzme Havuzu ve Spor Kompleksi", "Spor tesisi", 8400, 2012, 900, 56),
    ("Şirinevler Spor Salonu", "Spor tesisi", 3600, 2008, 500, 24),
    ("Hürriyet Semt Sahası", "Spor tesisi", 2200, 2017, 300, 12),
    ("Kocasinan Gençlik Spor Merkezi", "Spor tesisi", 4100, 2020, 620, 27),
    ("Çobançeşme Spor Tesisi", "Spor tesisi", 1900, 2022, 240, 11),
    ("Merkez Halk Kütüphanesi", "Kütüphane", 1600, 2004, 220, 14),
    ("Yenibosna Kütüphanesi", "Kütüphane", 980, 2013, 140, 9),
    ("Siyavuşpaşa Etüt Kütüphanesi", "Kütüphane", 760, 2019, 180, 7),
    ("Fevzi Çakmak Millet Kıraathanesi", "Kütüphane", 620, 2021, 120, 6),
    ("Belediye Sağlık Polikliniği", "Sağlık merkezi", 1400, 2006, 260, 38),
    ("Yenibosna Sağlık Birimi", "Sağlık merkezi", 720, 2016, 130, 17),
    ("Soğanlı Aile Sağlığı Destek Birimi", "Sağlık merkezi", 540, 2020, 90, 11),
    ("Kapalı Pazar Yeri - Şirinevler", "Pazar yeri", 9200, 2010, 2400, 16),
    ("Kapalı Pazar Yeri - Yenibosna", "Pazar yeri", 7800, 2013, 2000, 14),
    ("Kapalı Pazar Yeri - Kocasinan", "Pazar yeri", 6100, 2018, 1600, 12),
    ("Hanımlar Lokali ve Sosyal Tesis", "Sosyal tesis", 1300, 2011, 200, 15),
    ("Emekli Dinlenme Evi", "Sosyal tesis", 900, 2014, 150, 9),
    ("Belediye Aşevi", "Aşevi", 1700, 2008, 1500, 34),
    ("Kadın ve Aile Destek Merkezi", "Sosyal tesis", 1100, 2019, 180, 19),
    ("Gençlik Merkezi", "Gençlik merkezi", 2400, 2017, 350, 22),
    ("Belediye Kreş ve Gündüz Bakımevi", "Kreş", 1900, 2015, 180, 41),
    ("İkinci Kreş Birimi", "Kreş", 1200, 2022, 110, 26),
    ("Merkez Şantiye ve Atölye", "Depo/şantiye", 12500, 2003, 300, 128),
    ("Temizlik İşleri Şantiyesi", "Depo/şantiye", 8600, 2009, 200, 86),
    ("Park Bahçeler Fidanlık ve Depo", "Depo/şantiye", 5400, 2012, 120, 44),
    ("Hayvan Bakımevi ve Rehabilitasyon Merkezi", "Sağlık merkezi", 2600, 2014, 220, 23),
]


def uret(w):
    d = w.depo
    rng = w.r("base")

    # ---------------------------------------------------------------- ilce
    d.w(T.district).yaz(
        district_id=1, district_name="Bahçelievler", province_name="İstanbul",
        region_name="Marmara", area_km2=16.62, established_year=1992,
        mayor_name="Av. Necdet Karaduman", council_seat_count=45, neighborhood_count=11)

    # ------------------------------------------------------------ mahalleler
    w.mahalle_ham = MAHALLELER
    w.mahalleler = []
    for i, (ad, nfs, alan, seg, lat, lon) in enumerate(MAHALLELER, 1):
        bina_sayisi = int(nfs / rng.uniform(19, 26))
        sokak_sayisi = int(alan * rng.uniform(58, 78))
        yesil = alan * 1_000_000 * rng.uniform(0.030, 0.085)
        ad_soyad, _ = U.kisi_adi(rng, "E" if rng.random() < 0.85 else "K")
        d.w(T.neighborhood).yaz(
            neighborhood_id=i, neighborhood_name=ad, district_id=1,
            area_km2=round(alan, 3), street_count=sokak_sayisi,
            building_count=bina_sayisi, socioeconomic_segment=seg,
            green_area_m2=round(yesil, 2), mukhtar_name=ad_soyad,
            mukhtar_phone=f"02126{rng.randrange(100000, 999999)}",
            latitude=lat, longitude=lon)
        w.mahalleler.append({"id": i, "ad": ad, "nufus2026": nfs, "alan": alan,
                             "segment": seg, "bina": bina_sayisi, "sokak": sokak_sayisi})

    # --------------------------------------------------------------- sokaklar
    w.sokaklar = []
    w.sokak_by_mah = {m["id"]: [] for m in w.mahalleler}
    sid = 0
    for m in w.mahalleler:
        kullanilan = set()
        for _ in range(m["sokak"]):
            for _ in range(30):
                kok = rng.choice(SOKAK_ADI_KOK)
                tur = U.agirlikli(rng, SOKAK_TURU)
                if tur == "Sokak":
                    ad = f"{kok} Sokak" if rng.random() < 0.45 else f"{rng.randrange(1, 260)}. Sokak"
                elif tur == "Cadde":
                    ad = f"{kok} Caddesi"
                elif tur == "Bulvar":
                    ad = f"{kok} Bulvarı"
                else:
                    ad = f"{kok} Çıkmazı"
                if ad not in kullanilan:
                    break
            kullanilan.add(ad)
            sid += 1
            uzunluk = int(abs(rng.gauss(230, 130))) + 60
            d.w(T.street).yaz(
                street_id=sid, street_name=ad, street_type=tur,
                neighborhood_id=m["id"], length_m=uzunluk,
                lane_count=U.agirlikli(rng, [(1, 30), (2, 52), (3, 12), (4, 6)]),
                surface_type=U.agirlikli(rng, [("Asfalt", 68), ("Parke", 24),
                                               ("Beton", 6), ("Stabilize", 2)]),
                last_pavement_year=rng.randrange(2012, 2027))
            w.sokaklar.append((sid, m["id"]))
            w.sokak_by_mah[m["id"]].append(sid)

    # ------------------------------------------------------------ mudurlukler
    w.mudurlukler = []
    for i, (ad, byar, grup, norm) in enumerate(MUDURLUKLER, 1):
        yon, _ = U.kisi_adi(rng, "E" if rng.random() < 0.72 else "K")
        d.w(T.directorate).yaz(
            directorate_id=i, directorate_name=ad, deputy_mayor_area=byar,
            service_group=grup, headcount_budget=norm,
            cost_center_code=f"46.34.06.{i:02d}", manager_name=yon,
            building_name=rng.choice(["Belediye Ana Hizmet Binası", "Ek Hizmet Binası",
                                      "Merkez Şantiye ve Atölye", "Yenibosna Hizmet Birimi"]))
        w.mudurlukler.append({"id": i, "ad": ad, "grup": grup, "norm": norm})
    w.mud_by_ad = {m["ad"]: m["id"] for m in w.mudurlukler}

    # ---------------------------------------------------------------- unvanlar
    w.unvanlar = []
    for i, (ad, sinif, tur, dmin, dmax, endeks) in enumerate(UNVANLAR, 1):
        d.w(T.job_title).yaz(
            job_title_id=i, title_name=ad, staff_class=sinif, employment_type=tur,
            grade_min=dmin, grade_max=dmax, base_salary_index=endeks)
        w.unvanlar.append({"id": i, "ad": ad, "sinif": sinif, "tur": tur,
                           "dmin": dmin, "dmax": dmax, "endeks": endeks})

    # -------------------------------------------------- fonksiyonel/ekonomik kod
    w.fonksiyonel = []
    fid = 0
    for kod, ad, altlar in FONKSIYONEL:
        for akod, aad in altlar:
            fid += 1
            d.w(T.functional_code).yaz(functional_code_id=fid, code=kod, name=ad,
                                       sub_code=akod, sub_name=aad)
            w.fonksiyonel.append({"id": fid, "kod": kod, "ad": ad, "alt": akod})

    w.ekonomik = []
    eid = 0
    for yon, liste in (("Gider", EKONOMIK_GIDER), ("Gelir", EKONOMIK_GELIR)):
        for kod, ad, altlar in liste:
            for akod, aad in altlar:
                eid += 1
                d.w(T.economic_code).yaz(economic_code_id=eid, direction=yon, code=kod,
                                         name=ad, sub_code=akod, sub_name=aad)
                w.ekonomik.append({"id": eid, "yon": yon, "kod": kod, "ad": ad,
                                   "alt": akod, "alt_ad": aad})
    w.ekonomik_gider = [e for e in w.ekonomik if e["yon"] == "Gider"]
    w.ekonomik_gelir = [e for e in w.ekonomik if e["yon"] == "Gelir"]

    # ------------------------------------------------------------- mali yillar
    # NOT: fiscal_year satirlari gen_finance icinde yazilir; oradaki olcek
    # duzeltmesi (personel gideri payini yasal cerceveye yaklastirma) burada
    # hesaplanan degerleri yukari cekebiliyor.
    w.mali_yil = {}
    for i, y in enumerate(U.YILLAR, 1):
        butce = BUTCE[y]
        revize = butce * rng.uniform(1.04, 1.19)
        oran = rng.uniform(0.90, 0.99) if y < 2026 else 0.63
        gider = revize * oran
        gelir = gider * rng.uniform(0.97, 1.10)
        w.mali_yil[y] = {"id": i, "butce": butce, "revize": revize, "gider": gider,
                         "gelir": gelir,
                         "onay": dt.date(y - 1, 11, rng.randrange(10, 28))}

    # ---------------------------------------------------------------- tesisler
    w.tesisler = []
    for i, (ad, tur, alan, yil, kap, pers) in enumerate(TESIS_SABLON, 1):
        mah = rng.choice(w.mahalleler)["id"]
        isletme = alan * rng.uniform(900, 2600) * w.endeks(2025)
        gelir_ = isletme * (rng.uniform(0.25, 1.4) if tur in ("Spor tesisi", "Pazar yeri", "Sosyal tesis", "Kreş") else rng.uniform(0.0, 0.12))
        d.w(T.municipal_facility).yaz(
            municipal_facility_id=i, facility_name=ad, facility_type=tur,
            neighborhood_id=mah, area_m2=alan, opening_year=yil, capacity=kap,
            staff_count=pers, annual_operating_cost=U.para(isletme),
            annual_revenue=U.para(gelir_),
            is_accessible=yil >= 2012 or rng.random() < 0.5)
        w.tesisler.append({"id": i, "ad": ad, "tur": tur, "mah": mah,
                           "alan": alan, "yil": yil, "kap": kap})
    w.tesis_by_tur = {}
    for t in w.tesisler:
        w.tesis_by_tur.setdefault(t["tur"], []).append(t)

    # ------------------------------------------------------------- tedarikciler
    w.tedarikciler = []
    kategoriler = ["İnşaat ve taahhüt", "Temizlik hizmeti", "Güvenlik hizmeti",
                   "Araç kiralama", "Gıda", "Akaryakıt", "Bilişim", "Kırtasiye",
                   "Peyzaj", "Danışmanlık", "Enerji", "Sağlık malzemesi"]
    for i in range(1, 861):
        kat = U.agirlikli(rng, [(k, wgt) for k, wgt in zip(
            kategoriler, [22, 8, 5, 7, 12, 4, 9, 8, 7, 5, 4, 9])])
        yerel = rng.random() < 0.42
        kisi, _ = U.kisi_adi(rng)
        d.w(T.supplier).yaz(
            supplier_id=i, supplier_name=U.firma_adi(rng), tax_number=U.vkn(rng),
            category=kat,
            city="İstanbul" if yerel or rng.random() < 0.8 else rng.choice(
                ["Ankara", "İzmir", "Bursa", "Kocaeli", "Tekirdağ", "Konya"]),
            is_local=yerel,
            first_contract_date=U.rastgele_gun(rng, dt.date(2016, 1, 1), dt.date(2026, 6, 30)),
            blacklisted=rng.random() < 0.022, contact_person=kisi,
            phone=U.telefon(rng), iban=U.iban(rng))
        w.tedarikciler.append({"id": i, "kat": kat})
    w.ted_by_kat = {}
    for t in w.tedarikciler:
        w.ted_by_kat.setdefault(t["kat"], []).append(t["id"])
