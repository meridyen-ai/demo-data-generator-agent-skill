# -*- coding: utf-8 -*-
"""Issizlik, isyeri sicili, ruhsat, denetim ve belediye kurslari."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

SEKTOR = [
    ("Perakende", 26, ["Market", "Giyim mağazası", "Ayakkabı satışı", "Beyaz eşya satışı",
                       "Kuyumcu", "Kırtasiye", "Oyuncakçı", "Nalbur", "Eczane", "Manav"]),
    ("Gıda ve içecek", 19, ["Lokanta", "Kafe", "Fırın", "Pastane", "Kasap", "Büfe",
                            "Dönerci", "Çay ocağı", "Tatlıcı", "Balıkçı"]),
    ("Kişisel hizmetler", 11, ["Kuaför", "Güzellik salonu", "Terzi", "Kuru temizleme",
                               "Ayakkabı tamiri", "Fotoğrafçı"]),
    ("Sağlık", 7, ["Diş polikliniği", "Tıp merkezi", "Fizik tedavi merkezi",
                   "Optik", "Laboratuvar", "Veteriner kliniği"]),
    ("Eğitim", 5, ["Özel kurs merkezi", "Etüt merkezi", "Sürücü kursu", "Anaokulu",
                   "Yabancı dil kursu"]),
    ("İnşaat", 6, ["Müteahhitlik", "Yapı malzemesi satışı", "Doğrama imalatı",
                   "Tesisat hizmeti", "Boya badana"]),
    ("İmalat", 8, ["Tekstil atölyesi", "Konfeksiyon", "Matbaa", "Mobilya imalatı",
                   "Metal işleme", "Ambalaj üretimi", "Gıda üretimi"]),
    ("Ulaştırma", 5, ["Nakliyat", "Kargo şubesi", "Servis taşımacılığı", "Oto kiralama",
                      "Taksi durağı"]),
    ("Bilişim", 4, ["Yazılım firması", "Bilgisayar satış servis", "Cep telefonu satışı",
                    "Reklam ajansı"]),
    ("Finans", 3, ["Banka şubesi", "Sigorta acentesi", "Muhasebe bürosu", "Döviz bürosu"]),
    ("Konaklama", 2, ["Otel", "Apart otel", "Pansiyon"]),
    ("Toptan ticaret", 4, ["Gıda toptancısı", "Tekstil toptancısı", "Hırdavat toptancısı",
                           "İnşaat malzemesi toptancısı"]),
]

RUHSAT_TURU = [("Sıhhi Müessese", 62), ("Gayrisıhhi Müessese 3. Sınıf", 24),
               ("Gayrisıhhi Müessese 2. Sınıf", 7), ("Umuma Açık İstirahat ve Eğlence Yeri", 7)]

KURSLAR = [
    ("Bilgisayar İşletmenliği", "Bilişim"), ("Web Tasarım", "Bilişim"),
    ("Ofis Programları", "Bilişim"), ("Dijital Pazarlama", "Bilişim"),
    ("İngilizce Başlangıç", "Yabancı dil"), ("İngilizce Konuşma Kulübü", "Yabancı dil"),
    ("Arapça", "Yabancı dil"), ("Almanca", "Yabancı dil"),
    ("Kuaförlük", "Meslek edindirme"), ("Cilt Bakımı ve Güzellik", "Meslek edindirme"),
    ("Aşçılık ve Mutfak", "Meslek edindirme"), ("Pastacılık", "Meslek edindirme"),
    ("Terzilik ve Dikiş", "Meslek edindirme"), ("Hasta ve Yaşlı Bakımı", "Meslek edindirme"),
    ("Çocuk Bakımı", "Meslek edindirme"), ("Muhasebe Elemanı", "Meslek edindirme"),
    ("Kaynak Teknolojisi", "Meslek edindirme"), ("Elektrik Tesisatçılığı", "Meslek edindirme"),
    ("Ebru Sanatı", "El sanatları"), ("Hat Sanatı", "El sanatları"),
    ("Ahşap Boyama", "El sanatları"), ("Takı Tasarımı", "El sanatları"),
    ("Çini ve Seramik", "El sanatları"), ("Resim", "El sanatları"),
    ("Gitar", "Müzik"), ("Bağlama", "Müzik"), ("Piyano", "Müzik"),
    ("Ney", "Müzik"), ("Türk Sanat Müziği Korosu", "Müzik"),
    ("Yüzme", "Spor"), ("Tekvando", "Spor"), ("Satranç", "Spor"),
    ("Pilates", "Spor"), ("Jimnastik", "Spor"), ("Masa Tenisi", "Spor"),
    ("YKS Hazırlık", "Sınav hazırlık"), ("LGS Hazırlık", "Sınav hazırlık"),
    ("KPSS Hazırlık", "Sınav hazırlık"),
    ("Diksiyon ve Etkili Konuşma", "Kişisel gelişim"),
    ("Aile İçi İletişim Semineri", "Kişisel gelişim"),
]

MERKEZLER = ["Bahçelievler Kültür Merkezi", "Yenibosna Kültür ve Sanat Merkezi",
             "Soğanlı Kültür Merkezi", "Zafer Sanat Akademisi", "Gençlik Merkezi",
             "Hanımlar Lokali ve Sosyal Tesis", "Kadın ve Aile Destek Merkezi"]


def uret(w):
    d = w.depo
    rng = w.r("econ")

    # -------------------------------------------------------------- issizlik
    uid = 0
    for yil in U.YILLAR:
        for ceyrek in (1, 2, 3, 4):
            if yil == 2026 and ceyrek > 3:
                continue
            # ulke geneline benzer dalgalanma
            taban = {2019: 13.7, 2020: 13.2, 2021: 12.0, 2022: 10.4,
                     2023: 9.4, 2024: 8.7, 2025: 8.4, 2026: 8.9}[yil]
            taban += {1: 0.6, 2: -0.2, 3: -0.5, 4: 0.1}[ceyrek]
            for m in w.mahalleler:
                seg_ek = {"Alt-Orta": 2.9, "Orta": 0.0, "Üst-Orta": -2.1}[m["segment"]]
                for band, kat_orani, yas_ek in (("15-24", 0.44, 9.6), ("25-34", 0.79, 0.4),
                                                ("35-44", 0.81, -1.4), ("45-54", 0.68, -2.0),
                                                ("55-64", 0.38, -2.6)):
                    for cins in ("E", "K"):
                        nfs_band = int(w.nufus(m["id"], yil) * {
                            "15-24": 0.151, "25-34": 0.167, "35-44": 0.155,
                            "45-54": 0.125, "55-64": 0.096}[band] * (0.508 if cins == "E" else 0.492))
                        kat = kat_orani * (1.0 if cins == "E" else 0.52)
                        isgucu = int(nfs_band * kat * rng.uniform(0.95, 1.05))
                        oran = max(2.0, taban + seg_ek + yas_ek +
                                   (2.8 if cins == "K" else 0.0) + rng.uniform(-1.4, 1.4))
                        issiz = int(isgucu * oran / 100.0)
                        uid += 1
                        d.w(T.unemployment_stat).yaz(
                            unemployment_stat_id=uid, year=yil, quarter=ceyrek,
                            neighborhood_id=m["id"], age_band=band, gender=cins,
                            labor_force=isgucu, employed_count=isgucu - issiz,
                            unemployed_count=issiz, unemployment_rate=round(oran, 2),
                            participation_rate=round(kat * 100 * rng.uniform(0.97, 1.03), 2),
                            informal_employment_count=int((isgucu - issiz) *
                                                          rng.uniform(0.13, 0.29)))

    # --------------------------------------------------------------- isyerleri
    w.isyerleri = []
    sektor_agirlik = [((ad, alt), wgt) for ad, wgt, alt in SEKTOR]
    mah_agirlik = [(m["id"], m["nufus2026"] * (1.35 if m["segment"] != "Üst-Orta" else 1.0))
                   for m in w.mahalleler]
    bid = 0
    for _ in range(15200):
        bid += 1
        (sekt, altlar) = U.agirlikli(rng, sektor_agirlik)
        mid = U.agirlikli(rng, mah_agirlik)
        acilis = U.rastgele_gun(rng, dt.date(1994, 1, 1), dt.date(2026, 8, 1))
        if rng.random() < 0.55:
            acilis = U.rastgele_gun(rng, dt.date(2015, 1, 1), dt.date(2026, 8, 1))
        kapanis, durum = None, "Faal"
        if rng.random() < 0.21:
            kapanis = U.rastgele_gun(rng, max(acilis + dt.timedelta(days=120), U.BASLANGIC), U.BITIS)
            if kapanis <= acilis:
                kapanis = None
            else:
                durum = U.agirlikli(rng, [("Kapalı", 74), ("Devredildi", 18), ("Askıda", 8)])
        elif rng.random() < 0.03:
            durum = "Askıda"
        calisan = max(1, int(abs(rng.gauss(3.4, 4.6))) + 1)
        if sekt in ("İmalat", "Toptan ticaret", "Konaklama"):
            calisan = max(2, int(abs(rng.gauss(11, 14))) + 1)
        d.w(T.business).yaz(
            business_id=bid, business_name=U.firma_adi(rng), tax_number=U.vkn(rng),
            sector=sekt, nace_code=f"{rng.randrange(10, 96)}.{rng.randrange(10, 99)}",
            activity_description=rng.choice(altlar), neighborhood_id=mid,
            street_id=rng.choice(w.sokak_by_mah[mid]),
            legal_form=U.agirlikli(rng, [("Şahıs", 58), ("Limited Şirket", 33),
                                         ("Anonim Şirket", 7), ("Kooperatif", 1),
                                         ("Adi Ortaklık", 1)]),
            employee_count=calisan, open_date=acilis, close_date=kapanis, status=durum,
            area_m2=max(12, int(abs(rng.gauss(78, 90)))),
            risk_class=U.agirlikli(rng, [("Az tehlikeli", 71), ("Tehlikeli", 24),
                                         ("Çok tehlikeli", 5)]))
        w.isyerleri.append({"id": bid, "mah": mid, "sekt": sekt, "acilis": acilis,
                            "kapanis": kapanis, "durum": durum, "alan": 1})

    # ----------------------------------------------------------------- ruhsat
    lid = 0
    w.ruhsat_geliri = {}
    for b in w.isyerleri:
        adet = 1 + (1 if rng.random() < 0.22 else 0)
        for k in range(adet):
            lid += 1
            basvuru = b["acilis"] - dt.timedelta(days=rng.randrange(10, 120)) if k == 0 else \
                U.rastgele_gun(rng, max(b["acilis"], U.BASLANGIC), U.BITIS)
            durum = U.agirlikli(rng, [("Onaylandı", 87), ("Reddedildi", 5),
                                      ("Beklemede", 4), ("İptal edildi", 4)])
            sure = U.normal_int(rng, 21, 16, 1, 180)
            veris = basvuru + dt.timedelta(days=sure) if durum == "Onaylandı" else None
            harc = 0.0
            if durum == "Onaylandı" and veris and U.BASLANGIC <= veris <= U.BITIS:
                harc = 1250 * w.endeks(veris) * rng.uniform(0.5, 4.0)
                w.ruhsat_geliri.setdefault(veris, 0.0)
                w.ruhsat_geliri[veris] += harc
            d.w(T.business_license).yaz(
                business_license_id=lid, business_id=b["id"],
                license_no=f"R-{basvuru.year}-{lid:06d}",
                license_type=U.agirlikli(rng, RUHSAT_TURU),
                application_date=basvuru, issue_date=veris,
                expiry_date=None if not veris else veris + dt.timedelta(days=365 * 5),
                status=durum, fee_amount=U.para(harc), processing_days=sure,
                rejection_reason=None if durum != "Reddedildi" else U.agirlikli(
                    rng, [("Yapı kullanma izni yok", 26), ("İmar durumuna aykırı", 22),
                          ("Eksik belge", 24), ("Mesafe şartı sağlanmıyor", 14),
                          ("İtfaiye raporu olumsuz", 14)]))

    # ---------------------------------------------------------------- denetim
    zabita_pers = [p["id"] for p in w.personeller
                   if p["unvan"]["ad"] in ("Zabıta Memuru", "Zabıta Komiseri", "Zabıta Amiri")]
    iid = 0
    w.denetimler = []
    for b in w.isyerleri:
        bas = max(U.BASLANGIC, b["acilis"])
        bit = b["kapanis"] or U.BITIS
        if bit <= bas:
            continue
        adet = int((bit - bas).days / 365.0 * rng.uniform(0.6, 3.4))
        for _ in range(adet):
            iid += 1
            gun = U.rastgele_gun(rng, bas, bit)
            sonuc = U.agirlikli(rng, [("Uygun", 63), ("Uyarı verildi", 18),
                                      ("Ceza kesildi", 11), ("Süre verildi", 6),
                                      ("Faaliyetten men", 2)])
            puan = {"Uygun": U.normal_int(rng, 88, 7, 70, 100),
                    "Uyarı verildi": U.normal_int(rng, 72, 8, 50, 88),
                    "Süre verildi": U.normal_int(rng, 63, 9, 40, 80),
                    "Ceza kesildi": U.normal_int(rng, 52, 11, 20, 72),
                    "Faaliyetten men": U.normal_int(rng, 34, 10, 0, 55)}[sonuc]
            d.w(T.business_inspection).yaz(
                business_inspection_id=iid, business_id=b["id"], inspection_date=gun,
                inspection_type=U.agirlikli(rng, [("Rutin", 46), ("Şikayet üzerine", 22),
                                                  ("Ruhsat kontrolü", 12), ("Hijyen", 9),
                                                  ("Fiyat etiketi", 7), ("Gürültü", 4)]),
                inspector_employee_id=rng.choice(zabita_pers) if zabita_pers else None,
                result=sonuc,
                finding_count=0 if sonuc == "Uygun" else rng.randrange(1, 7),
                score=puan, follow_up_required=sonuc in ("Süre verildi", "Faaliyetten men"))
            w.denetimler.append((iid, gun, b["id"], b["mah"], sonuc))

    # ------------------------------------------------------------------ kurslar
    w.kurslar = []
    cid = 0
    for yil in U.YILLAR:
        for donem, ay_bas in (("Güz", 10), ("Bahar", 2), ("Yaz", 6)):
            if yil == 2026 and ay_bas == 10:
                continue
            adet = int(rng.uniform(58, 86))
            for _ in range(adet):
                cid += 1
                ad, kat = rng.choice(KURSLAR)
                bas = dt.date(yil, ay_bas, rng.randrange(1, 25))
                if bas > U.BITIS:
                    continue
                sure = rng.randrange(45, 130)
                kap = U.agirlikli(rng, [(15, 22), (20, 30), (25, 24), (30, 16), (40, 8)])
                saat = rng.choice([48, 60, 72, 90, 120, 160])
                ucret = 0.0 if rng.random() < 0.82 else round(180 * w.endeks(bas) * rng.uniform(0.6, 2.4), 2)
                mid = rng.choice(w.mahalleler)["id"]
                d.w(T.vocational_course).yaz(
                    vocational_course_id=cid, course_name=ad, category=kat,
                    term=f"{yil}-{donem}", start_date=bas,
                    end_date=min(U.BITIS, bas + dt.timedelta(days=sure)),
                    neighborhood_id=mid, venue_name=rng.choice(MERKEZLER),
                    instructor_name=U.kisi_adi(rng)[0], capacity=kap, total_hours=saat,
                    fee_amount=U.para(ucret),
                    cost_amount=U.para(saat * 380 * w.endeks(bas) * rng.uniform(0.7, 1.6)))
                w.kurslar.append({"id": cid, "bas": bas, "kap": kap, "kat": kat, "mah": mid})

    # ------------------------------------------------------------- kurs kayitlari
    eid = 0
    for k in w.kurslar:
        katilim = int(k["kap"] * rng.uniform(0.62, 1.12))
        havuz = w.vat_by_mah[k["mah"]] + w.vat_by_mah[rng.choice(w.mahalleler)["id"]]
        for _ in range(katilim):
            eid += 1
            durum = U.agirlikli(rng, [("Tamamladı", 66), ("Bıraktı", 19),
                                      ("Devam ediyor", 9), ("Kayıt iptal", 6)])
            devam = {"Tamamladı": round(rng.uniform(78, 100), 2),
                     "Bıraktı": round(rng.uniform(5, 55), 2),
                     "Devam ediyor": round(rng.uniform(60, 98), 2),
                     "Kayıt iptal": 0.0}[durum]
            d.w(T.course_enrollment).yaz(
                course_enrollment_id=eid, vocational_course_id=k["id"],
                citizen_id=rng.choice(havuz),
                enrollment_date=k["bas"] - dt.timedelta(days=rng.randrange(0, 30)),
                attendance_rate=devam, status=durum,
                certificate_issued=durum == "Tamamladı" and rng.random() < 0.93,
                employed_after_course=(durum == "Tamamladı" and
                                       k["kat"] == "Meslek edindirme" and rng.random() < 0.34),
                satisfaction_score=U.agirlikli(rng, [(5, 46), (4, 32), (3, 14), (2, 5), (1, 3)]))
