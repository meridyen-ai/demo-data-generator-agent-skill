# -*- coding: utf-8 -*-
"""Cozum Merkezi basvurulari ve belediye anketleri."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

# (ana kategori, alt kategori, sorumlu mudurluk, hedef saat, oncelik, agirlik)
KATEGORILER = [
    ("Temizlik", "Çöp toplanmadı", "Temizlik İşleri Müdürlüğü", 24, "Yüksek", 96),
    ("Temizlik", "Konteyner talebi", "Temizlik İşleri Müdürlüğü", 72, "Normal", 41),
    ("Temizlik", "Moloz/hafriyat şikayeti", "Temizlik İşleri Müdürlüğü", 48, "Normal", 34),
    ("Temizlik", "Sokak yıkama talebi", "Temizlik İşleri Müdürlüğü", 96, "Düşük", 22),
    ("Yollar ve altyapı", "Yol çukuru", "Fen İşleri Müdürlüğü", 72, "Yüksek", 68),
    ("Yollar ve altyapı", "Kaldırım bozukluğu", "Fen İşleri Müdürlüğü", 120, "Normal", 44),
    ("Yollar ve altyapı", "Rögar kapağı", "Fen İşleri Müdürlüğü", 24, "Acil", 19),
    ("Yollar ve altyapı", "Su birikintisi", "Fen İşleri Müdürlüğü", 48, "Yüksek", 26),
    ("Aydınlatma", "Sokak lambası yanmıyor", "Fen İşleri Müdürlüğü", 72, "Normal", 74),
    ("Park ve yeşil alan", "Park bakım talebi", "Park ve Bahçeler Müdürlüğü", 168, "Düşük", 38),
    ("Park ve yeşil alan", "Ağaç budama talebi", "Park ve Bahçeler Müdürlüğü", 168, "Düşük", 33),
    ("Park ve yeşil alan", "Oyun grubu arızası", "Park ve Bahçeler Müdürlüğü", 96, "Normal", 21),
    ("Zabıta", "Kaldırım işgali", "Zabıta Müdürlüğü", 24, "Normal", 47),
    ("Zabıta", "Gürültü şikayeti", "Zabıta Müdürlüğü", 12, "Yüksek", 52),
    ("Zabıta", "Seyyar satıcı", "Zabıta Müdürlüğü", 24, "Normal", 31),
    ("Zabıta", "Ruhsatsız işyeri ihbarı", "Ruhsat ve Denetim Müdürlüğü", 72, "Normal", 24),
    ("Sosyal yardım", "Yardım başvurusu bilgisi", "Sosyal Yardım İşleri Müdürlüğü", 72, "Normal", 58),
    ("Sosyal yardım", "Gıda yardımı talebi", "Sosyal Yardım İşleri Müdürlüğü", 120, "Normal", 44),
    ("Sosyal yardım", "Engelli hizmet talebi", "Sosyal Yardım İşleri Müdürlüğü", 72, "Yüksek", 18),
    ("İmar", "İmar durumu sorgusu", "İmar ve Şehircilik Müdürlüğü", 120, "Normal", 29),
    ("İmar", "Kaçak yapı ihbarı", "Yapı Kontrol Müdürlüğü", 48, "Yüksek", 26),
    ("İmar", "Kentsel dönüşüm bilgisi", "Kentsel Dönüşüm ve Afet İşleri Müdürlüğü", 120, "Normal", 17),
    ("Veteriner", "Sokak hayvanı ihbarı", "Veteriner İşleri Müdürlüğü", 24, "Yüksek", 42),
    ("Veteriner", "Kısırlaştırma talebi", "Veteriner İşleri Müdürlüğü", 168, "Düşük", 16),
    ("Kültür ve etkinlik", "Etkinlik bilgisi", "Kültür ve Sosyal İşler Müdürlüğü", 48, "Düşük", 27),
    ("Kültür ve etkinlik", "Kurs kayıt talebi", "Kültür ve Sosyal İşler Müdürlüğü", 72, "Normal", 34),
    ("Vergi ve tahsilat", "Emlak vergisi sorgusu", "Mali Hizmetler Müdürlüğü", 48, "Normal", 51),
    ("Vergi ve tahsilat", "Borç yapılandırma talebi", "Mali Hizmetler Müdürlüğü", 72, "Normal", 28),
    ("Ulaşım", "Trafik ve park sorunu", "Ulaşım Hizmetleri Müdürlüğü", 72, "Normal", 24),
    ("Sağlık", "Poliklinik randevu", "Sağlık İşleri Müdürlüğü", 24, "Normal", 22),
    ("Genel", "Bilgi edinme başvurusu", "Yazı İşleri Müdürlüğü", 360, "Düşük", 26),
    ("Genel", "Öneri ve teşekkür", "Basın Yayın ve Halkla İlişkiler Müdürlüğü", 168, "Düşük", 21),
]

ANKET_SORULARI = [
    ("Belediyenin çöp toplama hizmetinden ne kadar memnunsunuz?", "Temizlik"),
    ("Sokak ve caddelerin temizliğini nasıl değerlendiriyorsunuz?", "Temizlik"),
    ("Mahallenizdeki yolların durumundan memnun musunuz?", "Yollar ve altyapı"),
    ("Kaldırımların yaya kullanımına uygunluğunu nasıl buluyorsunuz?", "Yollar ve altyapı"),
    ("Sokak aydınlatmasını yeterli buluyor musunuz?", "Yollar ve altyapı"),
    ("Park ve yeşil alanların sayısını yeterli buluyor musunuz?", "Park ve yeşil alan"),
    ("Çocuk oyun alanlarının bakımından memnun musunuz?", "Park ve yeşil alan"),
    ("Zabıta hizmetlerinden ne kadar memnunsunuz?", "Zabıta"),
    ("Gürültü şikayetlerine verilen yanıt hızını nasıl değerlendiriyorsunuz?", "Zabıta"),
    ("Sosyal yardım hizmetlerine erişim kolaylığını nasıl buluyorsunuz?", "Sosyal yardım"),
    ("Belediyenin düzenlediği kültürel etkinlikleri yeterli buluyor musunuz?", "Kültür ve etkinlik"),
    ("Spor tesislerinden yararlanma imkanını nasıl değerlendiriyorsunuz?", "Kültür ve etkinlik"),
    ("Belediye çağrı merkezine ulaşmakta zorluk yaşıyor musunuz?", "Çağrı merkezi"),
    ("Başvurunuza verilen yanıt süresinden memnun musunuz?", "Çağrı merkezi"),
    ("İmar ve ruhsat işlemlerinin şeffaflığını nasıl buluyorsunuz?", "İmar"),
    ("Belediye yönetiminin genel performansını nasıl değerlendiriyorsunuz?", "Genel yönetim"),
    ("Belediye harcamalarının şeffaflığından memnun musunuz?", "Genel yönetim"),
    ("Toplu ulaşım ve trafik düzenlemelerini nasıl buluyorsunuz?", "Ulaşım"),
    ("Mahallenizde kendinizi güvende hissediyor musunuz?", "Güvenlik"),
    ("Çevrenizdeki gürültü seviyesinden rahatsız oluyor musunuz?", "Gürültü"),
]

LIKERT = [("Çok memnunum", 5), ("Memnunum", 4), ("Kararsızım", 3),
          ("Memnun değilim", 2), ("Hiç memnun değilim", 1)]


def uret(w):
    d = w.depo
    rng = w.r("civic")
    mud = w.mud_by_ad

    # --------------------------------------------------------------- kategoriler
    w.kategoriler = []
    for i, (ana, alt, mad, hedef, oncelik, agirlik) in enumerate(KATEGORILER, 1):
        d.w(T.request_category).yaz(
            request_category_id=i, category_name=ana, sub_category_name=alt,
            responsible_directorate_id=mud[mad], target_resolution_hours=hedef,
            priority=oncelik)
        w.kategoriler.append({"id": i, "ana": ana, "alt": alt, "mud": mud[mad],
                              "hedef": hedef, "oncelik": oncelik, "w": agirlik})

    kat_agirlik = [(k, k["w"]) for k in w.kategoriler]

    # ------------------------------------------------------------- basvurular
    personel_havuz = [p["id"] for p in w.personeller if p["durum"] != "Ayrıldı"]
    sid, lid = 0, 0
    for gun in U.gunler():
        taban = 58 + 4.2 * (gun.year - 2019)
        if gun.weekday() >= 5:
            taban *= 0.42
        if gun.month in (7, 8):
            taban *= 1.12
        adet = U.normal_int(rng, int(taban), int(taban * 0.28), 3, 240)
        for _ in range(adet):
            sid += 1
            k = U.agirlikli(rng, kat_agirlik)
            m = U.agirlikli(rng, [(mm["id"], mm["nufus2026"]) for mm in w.mahalleler])
            saat = U.agirlikli(rng, [(9, 14), (10, 13), (11, 12), (12, 8), (13, 9),
                                     (14, 12), (15, 11), (16, 9), (17, 6), (20, 3),
                                     (22, 2), (2, 1)])
            olusma = dt.datetime(gun.year, gun.month, gun.day, saat,
                                 rng.randrange(0, 60), rng.randrange(0, 60))
            tip = U.agirlikli(rng, [("Şikayet", 54), ("Talep", 29), ("İhbar", 9),
                                    ("Bilgi edinme", 4), ("Öneri", 3), ("Teşekkür", 1)])
            kanal = U.agirlikli(rng, [("Çağrı merkezi", 32 - (gun.year - 2019) * 1.6),
                                      ("Mobil uygulama", 12 + (gun.year - 2019) * 3.1),
                                      ("Web sitesi", 17), ("CİMER", 9),
                                      ("Şahsen başvuru", 11), ("Sosyal medya", 7),
                                      ("Muhtarlık", 5), ("WhatsApp", 7)])
            hedef = k["hedef"]
            r = rng.random()
            durum = ("Çözüldü" if r < 0.845 else "İşlemde" if r < 0.90 else
                     "Başka kuruma yönlendirildi" if r < 0.945 else
                     "Reddedildi" if r < 0.972 else "Mükerrer" if r < 0.99 else "Yeni")
            ilk_donus = round(max(0.2, rng.gauss(hedef * 0.16, hedef * 0.12)), 2)
            if durum == "Çözüldü":
                cozum = round(max(0.5, rng.gauss(hedef * 0.70, hedef * 0.42)), 2)
                kapanis = olusma + dt.timedelta(hours=cozum)
                if kapanis.date() > U.BITIS:
                    kapanis, cozum, durum = None, None, "İşlemde"
            else:
                cozum, kapanis = None, None
            sla = (cozum is not None and cozum <= hedef)
            d.w(T.service_request).yaz(
                service_request_id=sid, request_no=f"ÇM-{gun.year}-{sid:07d}",
                created_at=olusma, created_date=gun, request_category_id=k["id"],
                request_type=tip, channel=kanal,
                citizen_id=rng.choice(w.vat_by_mah[m]) if rng.random() < 0.88 else None,
                neighborhood_id=m, street_id=rng.choice(w.sokak_by_mah[m]),
                assigned_directorate_id=k["mud"],
                assigned_employee_id=rng.choice(personel_havuz),
                subject=f"{k['ana']} - {k['alt']}", priority=k["oncelik"], status=durum,
                first_response_hours=ilk_donus, resolution_hours=cozum,
                closed_at=kapanis, sla_met=sla,
                reopened_count=U.agirlikli(rng, [(0, 92), (1, 6), (2, 2)]),
                satisfaction_score=(U.agirlikli(rng, [(5, 34), (4, 27), (3, 16), (2, 11), (1, 12)])
                                    if durum == "Çözüldü" and rng.random() < 0.42 else None))
            # yasam dongusu
            adimlar = [("Kayıt açıldı", None, "Yeni", olusma),
                       ("Müdürlüğe atandı", "Yeni", "İşlemde",
                        olusma + dt.timedelta(hours=ilk_donus * 0.4)),
                       ("Personele atandı", "İşlemde", "İşlemde",
                        olusma + dt.timedelta(hours=ilk_donus))]
            if durum == "Çözüldü" and kapanis:
                adimlar.append(("Yerinde inceleme", "İşlemde", "İşlemde",
                                olusma + dt.timedelta(hours=(cozum or 1) * 0.5)))
                adimlar.append(("Çözüldü", "İşlemde", "Çözüldü", kapanis))
            elif durum == "Başka kuruma yönlendirildi":
                adimlar.append(("Yönlendirildi", "İşlemde", "Başka kuruma yönlendirildi",
                                olusma + dt.timedelta(hours=ilk_donus * 2)))
            for eylem, eski, yeni, zaman in adimlar:
                if zaman.date() > U.BITIS:
                    continue
                lid += 1
                d.w(T.service_request_log).yaz(
                    service_request_log_id=lid, service_request_id=sid, log_at=zaman,
                    action=eylem, from_status=eski, to_status=yeni,
                    directorate_id=k["mud"],
                    note=rng.choice(["Ekip yönlendirildi.", "Vatandaş bilgilendirildi.",
                                     "Saha kontrolü yapıldı.", "İlgili birime iletildi.",
                                     "Talep karşılandı.", "Ek bilgi istendi.", None]))

    # ------------------------------------------------------------------ anketler
    anid, qid, rid, aid = 0, 0, 0, 0
    for yil in U.YILLAR:
        anketler = [
            ("Genel Memnuniyet Araştırması", "Genel memnuniyet", 2400, "Yüz yüze"),
            ("Hizmet Değerlendirme Anketi", "Hizmet değerlendirme", 1200, "Telefon"),
            ("Mahalle İhtiyaç Analizi", "İhtiyaç analizi", 900, "Yüz yüze"),
            ("Dijital Hizmetler Memnuniyet Anketi", "Hizmet değerlendirme", 1600, "Online"),
            ("Katılımcı Bütçe Anketi", "Bütçe katılım", 800, "Mobil uygulama"),
        ]
        if yil == 2026:
            anketler = anketler[:3]
        for ad, tur, hedef_n, yontem in anketler:
            anid += 1
            bas = dt.date(yil, rng.randrange(2, 11), rng.randrange(1, 28))
            if bas > U.BITIS:
                continue
            bit = min(U.BITIS, bas + dt.timedelta(days=rng.randrange(20, 70)))
            gercek = int(hedef_n * rng.uniform(0.72, 1.05))
            sorular = rng.sample(ANKET_SORULARI, rng.randrange(9, 15))
            # yil ilerledikce hafif memnuniyet artisi
            taban_memnuniyet = 3.28 + 0.055 * (yil - 2019)
            soru_ids = []
            for i, (metin, konu) in enumerate(sorular, 1):
                qid += 1
                soru_ids.append((qid, konu))
                d.w(T.survey_question).yaz(
                    survey_question_id=qid, survey_id=anid, question_no=i,
                    question_text=metin, question_topic=konu,
                    question_type="5'li Likert")
            toplam_puan, toplam_adet = 0.0, 0
            for _ in range(gercek):
                rid += 1
                m = U.agirlikli(rng, [(mm["id"], mm["nufus2026"]) for mm in w.mahalleler])
                cid = rng.choice(w.vat_by_mah[m])
                _, _, dogum, cins = w.vatandaslar[cid - 1]
                yas = yil - dogum.year
                band = ("18-24" if yas < 25 else "25-34" if yas < 35 else
                        "35-44" if yas < 45 else "45-54" if yas < 55 else
                        "55-64" if yas < 65 else "65+")
                tamam = rng.random() < 0.91
                yanit_gun = U.rastgele_gun(rng, bas, bit)
                d.w(T.survey_respondent).yaz(
                    survey_respondent_id=rid, survey_id=anid, citizen_id=cid,
                    neighborhood_id=m, response_date=yanit_gun, age_band=band,
                    gender=cins,
                    education_level=U.agirlikli(rng, [("İlkokul", 18), ("Ortaokul", 16),
                                                      ("Lise", 32), ("Ön lisans", 11),
                                                      ("Lisans", 19), ("Lisansüstü", 4)]),
                    employment_status=U.agirlikli(rng, [("Çalışıyor", 48), ("İşsiz", 11),
                                                        ("Emekli", 17), ("Ev hanımı", 17),
                                                        ("Öğrenci", 7)]),
                    years_in_district=U.normal_int(rng, 18, 12, 1, 60), completed=tamam)
                if not tamam:
                    continue
                seg = w.mahalleler[m - 1]["segment"]
                seg_ek = {"Alt-Orta": -0.22, "Orta": 0.0, "Üst-Orta": 0.18}[seg]
                for sq, konu in soru_ids:
                    konu_ek = {"Temizlik": 0.16, "Yollar ve altyapı": -0.20,
                               "Park ve yeşil alan": 0.22, "Zabıta": -0.08,
                               "Sosyal yardım": 0.26, "Kültür ve etkinlik": 0.19,
                               "Çağrı merkezi": -0.14, "İmar": -0.33,
                               "Genel yönetim": 0.05, "Ulaşım": -0.26,
                               "Güvenlik": 0.02, "Gürültü": -0.30}.get(konu, 0.0)
                    ort = taban_memnuniyet + seg_ek + konu_ek
                    deger = int(min(5, max(1, round(rng.gauss(ort, 1.05)))))
                    etiket = [e for e, v in LIKERT if v == deger][0]
                    aid += 1
                    toplam_puan += deger
                    toplam_adet += 1
                    d.w(T.survey_answer).yaz(
                        survey_answer_id=aid, survey_id=anid, survey_question_id=sq,
                        survey_respondent_id=rid, neighborhood_id=m,
                        answer_value=deger, answer_label=etiket,
                        answer_text=None if rng.random() > 0.03 else rng.choice(
                            ["Hizmetlerden genel olarak memnunum.",
                             "Yol ve kaldırım sorunları çözülmeli.",
                             "Park sayısı artırılmalı.",
                             "Çöp toplama saatleri düzenlenmeli.",
                             "Sosyal yardım süreci hızlandırılmalı.",
                             "Otopark sorunu büyük.",
                             "Belediye çalışanları ilgili ve nazik."]))
            d.w(T.survey).yaz(
                survey_id=anid, survey_name=f"{yil} {ad}", survey_type=tur,
                start_date=bas, end_date=bit, method=yontem,
                target_sample_size=hedef_n, actual_sample_size=gercek,
                margin_of_error=round(98.0 / (gercek ** 0.5), 2),
                conducted_by=U.agirlikli(rng, [("Araştırma şirketi", 52),
                                               ("Belediye ekibi", 34),
                                               ("Üniversite", 14)]),
                cost_amount=U.para(gercek * 88 / w.endeks(2026) * w.endeks(bas)),
                overall_satisfaction=round(toplam_puan / toplam_adet, 2) if toplam_adet else None)
