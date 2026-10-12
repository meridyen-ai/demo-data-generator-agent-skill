# -*- coding: utf-8 -*-
"""Personel, bordro, izin, mesai, egitim, performans."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

# unvan endeksi 1.00 = 2019 yilinda aylik brut (TL)
BRUT_TABAN_2019 = 2300.0

# mudurluk adina gore unvan agirliklari (anahtar kelime -> [(unvan, agirlik)])
UNVAN_PROFILI = {
    "Temizlik İşleri": [("Temizlik Personeli", 74), ("Şoför", 12), ("Şef", 3),
                        ("Çevre Mühendisi", 2), ("Memur", 5), ("Tekniker", 2),
                        ("Müdür", 1), ("Müdür Yardımcısı", 1)],
    "Park ve Bahçeler": [("Park Bahçe Personeli", 68), ("Peyzaj Mimarı", 5), ("Şoför", 8),
                         ("Tekniker", 6), ("Memur", 6), ("Şef", 4), ("Müdür", 1),
                         ("Müdür Yardımcısı", 2)],
    "Zabıta": [("Zabıta Memuru", 74), ("Zabıta Komiseri", 12), ("Zabıta Amiri", 5),
               ("Memur", 5), ("Şoför", 3), ("Müdür", 1)],
    "Fen İşleri": [("İnşaat Mühendisi", 14), ("Tekniker", 16), ("Teknisyen", 14),
                   ("İş Makinesi Operatörü", 12), ("Şoför", 14), ("Mimar", 5),
                   ("Harita Mühendisi", 5), ("Makine Mühendisi", 5), ("Memur", 9),
                   ("Şef", 4), ("Müdür Yardımcısı", 1), ("Müdür", 1)],
    "İmar ve Şehircilik": [("Mimar", 24), ("Şehir Plancısı", 14), ("İnşaat Mühendisi", 18),
                           ("Harita Mühendisi", 10), ("Tekniker", 12), ("Memur", 14),
                           ("Şef", 5), ("Müdür Yardımcısı", 2), ("Müdür", 1)],
    "Yapı Kontrol": [("İnşaat Mühendisi", 34), ("Mimar", 18), ("Tekniker", 22),
                     ("Memur", 16), ("Şef", 7), ("Müdür", 3)],
    "Plan ve Proje": [("Şehir Plancısı", 30), ("Mimar", 24), ("Harita Mühendisi", 14),
                      ("Tekniker", 12), ("Memur", 14), ("Müdür", 6)],
    "Kentsel Tasarım": [("Mimar", 34), ("Peyzaj Mimarı", 20), ("Şehir Plancısı", 16),
                        ("Tekniker", 12), ("Memur", 12), ("Müdür", 6)],
    "Kentsel Dönüşüm": [("İnşaat Mühendisi", 30), ("Mimar", 18), ("Harita Mühendisi", 12),
                        ("Avukat", 6), ("Memur", 20), ("Şef", 8), ("Müdür", 6)],
    "Etüd Proje": [("Mimar", 26), ("İnşaat Mühendisi", 24), ("Tekniker", 18),
                   ("Memur", 22), ("Müdür", 10)],
    "Mali Hizmetler": [("Memur", 34), ("Veri Hazırlama ve Kontrol İşletmeni", 22),
                       ("Mali Hizmetler Uzmanı", 14), ("Şef", 12), ("Uzman", 10),
                       ("Müdür Yardımcısı", 5), ("Müdür", 3)],
    "Sağlık İşleri": [("Doktor", 12), ("Diş Hekimi", 10), ("Hemşire", 26),
                      ("Psikolog", 8), ("Diyetisyen", 6), ("Memur", 22),
                      ("Büro Personeli", 12), ("Müdür", 4)],
    "Veteriner İşleri": [("Veteriner Hekim", 26), ("Teknisyen", 18), ("Şoför", 12),
                         ("Temizlik Personeli", 20), ("Memur", 18), ("Müdür", 6)],
    "Sosyal Yardım": [("Sosyal Çalışmacı", 22), ("Memur", 30), ("Büro Personeli", 22),
                      ("Psikolog", 8), ("Şoför", 8), ("Şef", 7), ("Müdür", 3)],
    "Kültür ve Sosyal": [("Eğitmen", 28), ("Büro Personeli", 22), ("Memur", 20),
                         ("Kütüphane Görevlisi", 12), ("Aşçı", 6), ("Şef", 8),
                         ("Müdür", 4)],
    "Gençlik ve Spor": [("Antrenör", 44), ("Büro Personeli", 20), ("Memur", 16),
                        ("Temizlik Personeli", 12), ("Şef", 5), ("Müdür", 3)],
    "Kadın ve Aile": [("Sosyal Çalışmacı", 26), ("Psikolog", 18), ("Eğitmen", 18),
                      ("Memur", 24), ("Müdür", 14)],
    "Basın Yayın": [("Büro Personeli", 26), ("Memur", 26), ("Çağrı Merkezi Personeli", 32),
                    ("Şef", 10), ("Müdür", 6)],
    "Bilgi İşlem": [("Bilgisayar Mühendisi", 34), ("Tekniker", 24), ("Memur", 22),
                    ("Uzman", 12), ("Müdür", 8)],
    "Hukuk İşleri": [("Avukat", 56), ("Memur", 30), ("Şef", 8), ("Müdür", 6)],
    "Destek Hizmetleri": [("Şoför", 26), ("Güvenlik Görevlisi", 22), ("Memur", 18),
                          ("Teknisyen", 12), ("Büro Personeli", 12), ("Şef", 7),
                          ("Müdür", 3)],
    "Ulaşım Hizmetleri": [("Şoför", 34), ("Tekniker", 18), ("Memur", 24),
                          ("Makine Mühendisi", 12), ("Müdür", 12)],
    "Ruhsat ve Denetim": [("Memur", 40), ("Uzman", 20), ("Tekniker", 14),
                          ("Çevre Mühendisi", 8), ("Şef", 12), ("Müdür", 6)],
    "Emlak ve İstimlak": [("Memur", 36), ("Harita Mühendisi", 16), ("Uzman", 16),
                          ("Veri Hazırlama ve Kontrol İşletmeni", 18), ("Şef", 8),
                          ("Müdür", 6)],
    "İnsan Kaynakları": [("Memur", 40), ("Uzman", 20), ("Veri Hazırlama ve Kontrol İşletmeni", 18),
                         ("Eğitmen", 8), ("Şef", 8), ("Müdür", 6)],
    "Yazı İşleri": [("Memur", 48), ("Veri Hazırlama ve Kontrol İşletmeni", 26),
                    ("Şef", 14), ("Müdür", 12)],
    "Muhtarlık İşleri": [("Memur", 56), ("Büro Personeli", 26), ("Müdür", 18)],
    "Strateji": [("Uzman", 40), ("Memur", 34), ("Şef", 14), ("Müdür", 12)],
    "Teftiş": [("Uzman", 46), ("Memur", 30), ("Müdür", 24)],
    "İşletme ve İştirakler": [("Memur", 38), ("Uzman", 22), ("Mali Hizmetler Uzmanı", 18),
                              ("Şef", 12), ("Müdür", 10)],
}
VARSAYILAN_PROFIL = [("Memur", 46), ("Büro Personeli", 22), ("Uzman", 14),
                     ("Şef", 12), ("Müdür", 6)]


def _profil(mudurluk_adi):
    for anahtar, prof in UNVAN_PROFILI.items():
        if mudurluk_adi.startswith(anahtar):
            return prof
    return VARSAYILAN_PROFIL


def uret(w):
    d = w.depo
    rng = w.r("hr")
    unvan_by_ad = {u["ad"]: u for u in w.unvanlar}

    # ---------------------------------------------------------------- personel
    w.personeller = []
    eid = 0
    for m in w.mudurlukler:
        prof = _profil(m["ad"])
        hedef = int(m["norm"] * rng.uniform(0.88, 1.06))
        # gecmiste ayrilanlar dahil toplam kadro
        toplam = int(hedef * 1.42)
        for k in range(toplam):
            eid += 1
            uad = U.agirlikli(rng, prof)
            u = unvan_by_ad[uad]
            cins = "E" if rng.random() < (0.74 if u["sinif"] in ("Teknik Hizmetler", "Yardımcı Hizmetler") else 0.55) else "K"
            ad, _ = U.kisi_adi(rng, cins)
            yas_giris = U.normal_int(rng, 28, 6, 19, 46)
            giris = U.rastgele_gun(rng, dt.date(1996, 1, 1), dt.date(2026, 7, 1))
            if rng.random() < 0.42:
                giris = U.rastgele_gun(rng, dt.date(2014, 1, 1), dt.date(2026, 7, 1))
            dogum = dt.date(giris.year - yas_giris, rng.randrange(1, 13), rng.randrange(1, 29))
            # ilk 'hedef' kisi calisiyor, kalanlar ayrilmis
            if k < hedef:
                ayrilis, neden, durum = None, None, U.agirlikli(
                    rng, [("Çalışıyor", 96), ("Ücretsiz izinde", 2), ("Askerlikte", 2)])
            else:
                en_erken = max(U.BASLANGIC, giris + dt.timedelta(days=200))
                if en_erken > U.BITIS:
                    en_erken = max(U.BASLANGIC, min(giris, U.BITIS))
                ayrilis = U.rastgele_gun(rng, en_erken, U.BITIS)
                yas_ayrilis = ayrilis.year - dogum.year
                neden = U.agirlikli(rng, [("Emeklilik", 34 if yas_ayrilis > 52 else 4),
                                          ("İstifa", 32), ("Nakil", 14),
                                          ("Sözleşme feshi", 16), ("Vefat", 3)])
                durum = "Ayrıldı"
            d.w(T.employee).yaz(
                employee_id=eid, employee_no=f"BLD{eid:05d}", full_name=ad,
                national_id=U.tc_no(rng), gender=cins, birth_date=dogum,
                directorate_id=m["id"], job_title_id=u["id"],
                employment_type=u["tur"],
                grade=rng.randrange(u["dmin"], u["dmax"] + 1),
                step=rng.randrange(1, 10), hire_date=giris,
                termination_date=ayrilis, termination_reason=neden, status=durum,
                education_level=_egitim(rng, u),
                union_member=rng.random() < (0.72 if u["tur"] in ("Sürekli işçi", "Memur") else 0.24),
                disability_quota=rng.random() < 0.031,
                work_location=rng.choice(["Belediye Ana Hizmet Binası", "Ek Hizmet Binası",
                                          "Merkez Şantiye ve Atölye", "Saha", "Yenibosna Hizmet Birimi"]),
                neighborhood_id=U.agirlikli(rng, [(mm["id"], mm["nufus2026"]) for mm in w.mahalleler]),
                phone=U.telefon(rng), iban=U.iban(rng))
            w.personeller.append({"id": eid, "mud": m["id"], "unvan": u, "cins": cins,
                                  "giris": giris, "ayrilis": ayrilis, "durum": durum,
                                  "tur": u["tur"], "dogum": dogum})

    w.aktif_personel = [p for p in w.personeller if p["durum"] != "Ayrıldı"]
    w.pers_by_mud = {}
    for p in w.personeller:
        w.pers_by_mud.setdefault(p["mud"], []).append(p)

    # ------------------------------------------------------------------ bordro
    pid = 0
    w.yillik_personel_gideri = {y: 0.0 for y in U.YILLAR}
    w.pers_gider = {}          # (yil, mudurluk_id) -> isveren maliyeti
    for p in w.personeller:
        endeks_unvan = p["unvan"]["endeks"]
        kidem_baz = rng.uniform(0.9, 1.1)
        for ay in U.aylar():
            if ay < p["giris"].replace(day=1):
                continue
            if p["ayrilis"] and ay > p["ayrilis"]:
                continue
            fe = w.endeks(ay)
            hizmet_yili = max(0, ay.year - p["giris"].year)
            taban = BRUT_TABAN_2019 * endeks_unvan * fe * rng.uniform(0.985, 1.015)
            kidem = taban * min(0.30, 0.011 * hizmet_yili) * kidem_baz
            ek_odeme = taban * (0.42 if p["tur"] == "Memur" else 0.18) * rng.uniform(0.9, 1.1)
            mesai = 0.0
            if p["unvan"]["ad"] in ("Zabıta Memuru", "Şoför", "Temizlik Personeli",
                                    "Park Bahçe Personeli", "İş Makinesi Operatörü",
                                    "Teknisyen", "Güvenlik Görevlisi") and rng.random() < 0.55:
                mesai = taban * rng.uniform(0.03, 0.19)
            aile = taban * 0.035 * rng.uniform(0, 1.6)
            yemek_yol = 1450 * fe * rng.uniform(0.9, 1.1)
            ikramiye = 0.0
            if ay.month in (1, 7):                    # sosyal denge / ikramiye
                ikramiye = taban * rng.uniform(0.45, 0.95)
            if ay.month in (4, 12) and p["tur"] in ("Sürekli işçi", "Şirket personeli"):
                ikramiye += taban * rng.uniform(0.4, 0.7)
            brut = taban + kidem + ek_odeme + mesai + aile + yemek_yol + ikramiye
            sgk_isci = brut * 0.15
            matrah = brut - sgk_isci
            oran = 0.15 if ay.month <= 6 else (0.20 if ay.month <= 10 else 0.27)
            istisna = 3100 * fe
            gv = max(0.0, matrah * oran - istisna)
            damga = max(0.0, (brut - 2600 * fe) * 0.00759)
            sendika = brut * 0.006 if rng.random() < 0.5 else 0.0
            diger = brut * rng.uniform(0, 0.05) if rng.random() < 0.12 else 0.0
            net = brut - sgk_isci - gv - damga - sendika - diger
            sgk_isveren = brut * 0.2275
            maliyet = brut + sgk_isveren
            pid += 1
            w.yillik_personel_gideri[ay.year] += maliyet
            k = (ay.year, p["mud"])
            w.pers_gider[k] = w.pers_gider.get(k, 0.0) + maliyet
            d.w(T.payroll).yaz(
                payroll_id=pid, employee_id=p["id"], period_month=ay, year=ay.year,
                directorate_id=p["mud"], employment_type=p["tur"],
                base_salary=U.para(taban), seniority_pay=U.para(kidem),
                additional_payment=U.para(ek_odeme), overtime_pay=U.para(mesai),
                family_allowance=U.para(aile), meal_transport_allowance=U.para(yemek_yol),
                bonus=U.para(ikramiye), gross_pay=U.para(brut),
                income_tax=U.para(gv), stamp_tax=U.para(damga),
                social_security_employee=U.para(sgk_isci), union_due=U.para(sendika),
                other_deductions=U.para(diger), net_pay=U.para(net),
                social_security_employer=U.para(sgk_isveren), employer_cost=U.para(maliyet),
                worked_days=U.agirlikli(rng, [(30, 86), (28, 4), (26, 4), (22, 3), (15, 3)]))

    # -------------------------------------------------------------------- izin
    lid = 0
    for p in w.personeller:
        bas = max(U.BASLANGIC, p["giris"])
        bit = p["ayrilis"] or U.BITIS
        if bit <= bas:
            continue
        yil_sayisi = max(1, (bit - bas).days / 365.0)
        for _ in range(int(yil_sayisi * rng.uniform(2.2, 4.6))):
            lid += 1
            tur = U.agirlikli(rng, [("Yıllık izin", 52), ("Mazeret izni", 16),
                                    ("Sağlık raporu", 18), ("Doğum izni", 3),
                                    ("Ücretsiz izin", 3), ("Refakat izni", 4),
                                    ("İdari izin", 4)])
            gun = {"Yıllık izin": U.normal_int(rng, 8, 5, 1, 30),
                   "Mazeret izni": rng.randrange(1, 4),
                   "Sağlık raporu": U.normal_int(rng, 4, 4, 1, 45),
                   "Doğum izni": rng.choice([56, 112, 16]),
                   "Ücretsiz izin": rng.randrange(15, 180),
                   "Refakat izni": rng.randrange(3, 20),
                   "İdari izin": rng.randrange(1, 5)}[tur]
            baslangic = U.rastgele_gun(rng, bas, bit)
            d.w(T.leave_record).yaz(
                leave_record_id=lid, employee_id=p["id"], leave_type=tur,
                start_date=baslangic, end_date=baslangic + dt.timedelta(days=gun - 1),
                day_count=gun, approved_by=U.kisi_adi(rng)[0],
                status=U.agirlikli(rng, [("Onaylandı", 93), ("Reddedildi", 4),
                                         ("İptal edildi", 3)]))

    # ------------------------------------------------------------------- mesai
    oid = 0
    mesai_unvanlari = ("Zabıta Memuru", "Zabıta Komiseri", "Şoför", "Temizlik Personeli",
                       "Park Bahçe Personeli", "İş Makinesi Operatörü", "Teknisyen",
                       "Güvenlik Görevlisi", "Tekniker")
    for p in w.personeller:
        if p["unvan"]["ad"] not in mesai_unvanlari:
            if rng.random() > 0.12:
                continue
        bas = max(U.BASLANGIC, p["giris"])
        bit = p["ayrilis"] or U.BITIS
        if bit <= bas:
            continue
        adet = int((bit - bas).days / 365.0 * rng.uniform(6, 22))
        for _ in range(adet):
            oid += 1
            gun = U.rastgele_gun(rng, bas, bit)
            neden = U.agirlikli(rng, [("Kar mücadelesi", 12 if gun.month in (1, 2, 12) else 0),
                                      ("Bayram nöbeti", 10), ("Etkinlik", 22),
                                      ("Acil müdahale", 16), ("Yoğunluk", 34),
                                      ("Seçim görevi", 8 if gun.year in (2019, 2023, 2024) else 1)])
            saat = round(rng.uniform(2, 12), 2)
            saatlik = BRUT_TABAN_2019 * p["unvan"]["endeks"] / 195.0 * 1.5 * w.endeks(gun)
            d.w(T.overtime_record).yaz(
                overtime_record_id=oid, employee_id=p["id"], work_date=gun,
                directorate_id=p["mud"], hours=saat, reason=neden,
                hourly_rate=U.para(saatlik), amount=U.para(saatlik * saat),
                is_holiday=gun.weekday() >= 5 or rng.random() < 0.08)

    # ------------------------------------------------------------------ egitim
    tid = 0
    egitimler = [
        ("İş Sağlığı ve Güvenliği Temel Eğitimi", "İş sağlığı ve güvenliği", 16),
        ("Yangın ve Acil Durum Tatbikatı", "İş sağlığı ve güvenliği", 8),
        ("4734 Sayılı Kamu İhale Kanunu Uygulamaları", "Mevzuat", 24),
        ("Belediye Gelirleri Kanunu ve Tahakkuk İşlemleri", "Mevzuat", 21),
        ("Analitik Bütçe ve Muhasebe Uygulamaları", "Mevzuat", 30),
        ("İmar Mevzuatı ve Uygulama Esasları", "Mevzuat", 28),
        ("Etkili İletişim ve Vatandaş Odaklı Hizmet", "Halkla ilişkiler", 12),
        ("Zabıta Hizmetlerinde Etik ve Yetki", "Mevzuat", 14),
        ("Coğrafi Bilgi Sistemleri (CBS) Kullanımı", "Teknik", 32),
        ("Kent Bilgi Sistemi ve E-Belediye", "Bilişim", 18),
        ("Excel ile Veri Analizi", "Bilişim", 20),
        ("KVKK ve Bilgi Güvenliği Farkındalığı", "Bilişim", 8),
        ("Kriz ve Afet Yönetimi", "Teknik", 16),
        ("Liderlik ve Ekip Yönetimi", "Yönetim", 24),
        ("Stres Yönetimi ve Motivasyon", "Kişisel gelişim", 10),
        ("Engelli Farkındalığı ve Erişilebilirlik", "Kişisel gelişim", 8),
        ("İlk Yardım Eğitimi", "İş sağlığı ve güvenliği", 16),
        ("Sıfır Atık Yönetim Sistemi", "Teknik", 12),
    ]
    saglayicilar = ["Marmara Belediyeler Birliği", "TODAİE Sürekli Eğitim",
                    "İSMEK İşbirliği", "Üniversite Sürekli Eğitim Merkezi",
                    "Kurum içi eğitmen", "Özel eğitim firması", "Çevre Şehircilik İl Müdürlüğü"]
    for p in w.personeller:
        bas = max(U.BASLANGIC, p["giris"])
        bit = p["ayrilis"] or U.BITIS
        if bit <= bas:
            continue
        for _ in range(int((bit - bas).days / 365.0 * rng.uniform(0.6, 2.4))):
            tid += 1
            ad, kat, saat = rng.choice(egitimler)
            gun = U.rastgele_gun(rng, bas, bit)
            d.w(T.training_record).yaz(
                training_record_id=tid, employee_id=p["id"], training_name=ad,
                training_category=kat, training_date=gun, hours=saat,
                provider=rng.choice(saglayicilar),
                cost_amount=U.para(saat * 95 * w.endeks(gun) * rng.uniform(0.5, 1.8)),
                exam_score=U.normal_int(rng, 78, 12, 30, 100),
                certificate_issued=rng.random() < 0.86)

    # -------------------------------------------------------------- performans
    prid = 0
    for p in w.personeller:
        for yil in U.YILLAR:
            if yil == 2026:
                continue
            if p["giris"].year > yil:
                continue
            if p["ayrilis"] and p["ayrilis"].year < yil:
                continue
            prid += 1
            puan = round(min(100, max(35, rng.gauss(76, 11))), 2)
            d.w(T.performance_review).yaz(
                performance_review_id=prid, employee_id=p["id"], year=yil,
                directorate_id=p["mud"], score=puan,
                grade="Çok iyi" if puan >= 88 else ("İyi" if puan >= 72 else
                                                    ("Orta" if puan >= 58 else "Geliştirilmeli")),
                attendance_score=round(min(100, max(40, rng.gauss(84, 10))), 2),
                citizen_feedback_score=round(min(100, max(30, rng.gauss(74, 14))), 2),
                promotion_recommended=puan >= 86 and rng.random() < 0.4)


def _egitim(rng, u):
    if u["sinif"] in ("Teknik Hizmetler", "Sağlık Hizmetleri", "Avukatlık Hizmetleri"):
        return U.agirlikli(rng, [("Lisans", 68), ("Lisansüstü", 16), ("Ön lisans", 14), ("Lise", 2)])
    if u["ad"] in ("Müdür", "Müdür Yardımcısı", "Uzman", "Mali Hizmetler Uzmanı"):
        return U.agirlikli(rng, [("Lisans", 62), ("Lisansüstü", 26), ("Ön lisans", 8), ("Lise", 4)])
    if u["tur"] == "Şirket personeli":
        return U.agirlikli(rng, [("İlkokul", 18), ("Ortaokul", 22), ("Lise", 46),
                                 ("Ön lisans", 11), ("Lisans", 3)])
    return U.agirlikli(rng, [("Lise", 42), ("Ön lisans", 22), ("Lisans", 27),
                             ("Ortaokul", 7), ("Lisansüstü", 2)])
