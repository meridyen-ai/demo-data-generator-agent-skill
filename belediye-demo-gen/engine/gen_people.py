# -*- coding: utf-8 -*-
"""Nufus, hane, vatandas, dogum, olum, goc, nikah, bosanma."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U
from .world import (YAS_BANTLARI, YAS_PAYI, EGITIM, EGITIM_AGIRLIK,
                    CALISMA_DURUMU, MESLEKLER, GELIR_BANDI)

OLUM_NEDENI = [
    ("Dolaşım sistemi hastalıkları", 0.355,
     ["İskemik kalp hastalığı", "Serebrovasküler hastalık", "Kalp yetmezliği",
      "Hipertansif kalp hastalığı", "Aort anevrizması"]),
    ("Kanser", 0.198,
     ["Akciğer kanseri", "Kolorektal kanser", "Mide kanseri", "Meme kanseri",
      "Prostat kanseri", "Pankreas kanseri", "Lösemi"]),
    ("Solunum sistemi hastalıkları", 0.121,
     ["KOAH", "Pnömoni", "Astım", "Solunum yetmezliği"]),
    ("Enfeksiyon hastalıkları", 0.052,
     ["Sepsis", "Tüberküloz", "Menenjit", "Hastane enfeksiyonu"]),
    ("Sinir sistemi hastalıkları", 0.078,
     ["Alzheimer hastalığı", "Parkinson hastalığı", "Demans"]),
    ("Kaza ve yaralanma", 0.049,
     ["Trafik kazası", "Düşme", "İş kazası", "Zehirlenme", "Yangın"]),
    ("Diğer", 0.147,
     ["Diyabet komplikasyonu", "Kronik böbrek yetmezliği", "Karaciğer sirozu",
      "Sindirim sistemi hastalığı", "Belirlenemeyen"]),
]

HASTANELER = ["Bahçelievler Devlet Hastanesi", "Özel Medicana Bahçelievler",
              "İstanbul Eğitim ve Araştırma Hastanesi", "Özel Yenibosna Hastanesi",
              "Bakırköy Dr. Sadi Konuk EAH", "Özel Şirinevler Tıp Merkezi",
              "Kanuni Sultan Süleyman EAH", "Evde doğum"]

NIKAH_SALONLARI = ["Bahçelievler Belediyesi Merkez Nikah Salonu",
                   "Yenibosna Nikah Salonu", "Kültür Merkezi Nikah Salonu",
                   "Zafer Nikah Salonu"]


def _yas_bandi(yas):
    if yas >= 80:
        return "80+"
    return YAS_BANTLARI[min(len(YAS_BANTLARI) - 2, yas // 5)]


def uret(w):
    d = w.depo
    rng = w.r("people")

    # ------------------------------------------------------- nufus istatistigi
    pid = 0
    for yil in U.YILLAR:
        for m in w.mahalleler:
            toplam = w.nufus(m["id"], yil)
            yabanci_oran = {"Alt-Orta": 0.085, "Orta": 0.052, "Üst-Orta": 0.031}[m["segment"]]
            yabanci_oran *= (0.55 + 0.09 * (yil - 2019))
            for band, pay in zip(YAS_BANTLARI, YAS_PAYI):
                for cins in ("E", "K"):
                    pay_c = pay * (0.508 if cins == "E" else 0.492)
                    n = int(round(toplam * pay_c * rng.uniform(0.94, 1.06)))
                    pid += 1
                    d.w(T.population_stat).yaz(
                        population_stat_id=pid, year=yil, neighborhood_id=m["id"],
                        age_band=band, gender=cins, population=n,
                        citizen_foreign_count=int(n * yabanci_oran * rng.uniform(0.5, 1.5)))

    # ------------------------------------------------------------------ haneler
    HANE = 58000
    w.haneler = []
    mah_agirlik = [(m["id"], m["nufus2026"]) for m in w.mahalleler]
    for hid in range(1, HANE + 1):
        mid = U.agirlikli(rng, mah_agirlik)
        seg = w.mahalleler[mid - 1]["segment"]
        uye = U.agirlikli(rng, [(1, 14), (2, 24), (3, 25), (4, 21), (5, 10), (6, 4), (7, 2)])
        cocuk = 0 if uye <= 2 else rng.randrange(0, max(1, uye - 1))
        yasli = U.agirlikli(rng, [(0, 76), (1, 17), (2, 7)])
        gelir_kayma = {"Alt-Orta": -1, "Orta": 0, "Üst-Orta": 1}[seg]
        gi = min(5, max(0, U.agirlikli(rng, [(0, 16), (1, 26), (2, 29), (3, 18), (4, 8), (5, 3)]) + gelir_kayma))
        sokaklar = w.sokak_by_mah[mid]
        d.w(T.household).yaz(
            household_id=hid, neighborhood_id=mid, street_id=rng.choice(sokaklar),
            member_count=uye, child_count=cocuk, elderly_count=yasli,
            disabled_count=1 if rng.random() < 0.062 else 0,
            tenure_type=U.agirlikli(rng, [("Ev sahibi", 54), ("Kiracı", 42),
                                          ("Lojman", 1), ("Diğer", 3)]),
            dwelling_type=U.agirlikli(rng, [("Apartman dairesi", 88), ("Müstakil ev", 6),
                                            ("Rezidans", 4), ("Gecekondu", 2)]),
            heating_type=U.agirlikli(rng, [("Doğalgaz kombi", 74), ("Merkezi sistem", 17),
                                           ("Elektrik", 6), ("Soba", 3)]),
            income_band=GELIR_BANDI[gi],
            registered_at=U.rastgele_gun(rng, dt.date(2015, 1, 1), U.BITIS))
        w.haneler.append((hid, mid, uye, gi))

    # --------------------------------------------------------------- vatandaslar
    VATANDAS = 132000
    w.vatandaslar = []          # (id, mah_id, dogum_tarihi, cinsiyet)
    w.vat_by_mah = {m["id"]: [] for m in w.mahalleler}
    for cid in range(1, VATANDAS + 1):
        hane = w.haneler[rng.randrange(len(w.haneler))]
        hid, mid, uye, gi = hane
        cins = "E" if rng.random() < 0.497 else "K"
        # belediye ile temas eden nufus yetiskin agirlikli
        yas = int(U.agirlikli(rng, [(22, 10), (28, 14), (34, 15), (40, 14), (46, 12),
                                    (52, 10), (58, 9), (64, 7), (70, 5), (78, 4)])
                  + rng.randrange(0, 6))
        dogum = dt.date(2026 - yas, rng.randrange(1, 13), rng.randrange(1, 29))
        medeni = U.agirlikli(rng, [("Evli", 62), ("Bekar", 24), ("Boşanmış", 8), ("Dul", 6)]) \
            if yas >= 25 else U.agirlikli(rng, [("Bekar", 78), ("Evli", 22)])
        egt = U.agirlikli(rng, list(zip(EGITIM, EGITIM_AGIRLIK)))
        if yas >= 65:
            egt = U.agirlikli(rng, [("İlkokul", 44), ("Ortaokul", 18), ("Lise", 22),
                                    ("Okur-yazar değil", 8), ("Lisans", 8)])
        if yas >= 62:
            calisma = U.agirlikli(rng, [("Emekli", 74), ("Çalışıyor", 9),
                                        ("Ev hanımı", 12), ("Çalışamaz", 5)])
        else:
            calisma = U.agirlikli(rng, [("Çalışıyor", 56), ("İşsiz", 12), ("Ev hanımı", 19),
                                        ("Emekli", 6), ("Öğrenci", 4), ("Çalışamaz", 3)])
        ad, _ = U.kisi_adi(rng, cins)
        d.w(T.citizen).yaz(
            citizen_id=cid, national_id=U.tc_no(rng), full_name=ad, gender=cins,
            birth_date=dogum, marital_status=medeni, education_level=egt,
            employment_status=calisma,
            occupation=rng.choice(MESLEKLER) if calisma in ("Çalışıyor", "Emekli") else None,
            disability_status=U.agirlikli(rng, [("Yok", 934), ("Bedensel", 22), ("Görme", 10),
                                                ("İşitme", 9), ("Zihinsel", 8), ("Süreli hastalık", 17)]),
            neighborhood_id=mid, household_id=hid,
            phone=U.telefon(rng),
            email=None if rng.random() < 0.42 else f"kullanici{cid}@eposta.com",
            is_household_head=rng.random() < 0.42,
            registered_at=U.rastgele_gun(rng, dt.date(2016, 1, 1), U.BITIS),
            kyk_card_flag=rng.random() < 0.31)
        w.vatandaslar.append((cid, mid, dogum, cins))
        w.vat_by_mah[mid].append(cid)

    # ------------------------------------------------------------------ dogumlar
    bid = 0
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        # kaba dogurganlik hizi zamanla dusuyor
        khd = 14.2 - 0.55 * (yil - 2019)
        for m in w.mahalleler:
            n = int(w.nufus(m["id"], yil) / 1000.0 * khd * gun_orani * rng.uniform(0.88, 1.12))
            for _ in range(n):
                bid += 1
                tarih = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
                sezaryen = rng.random() < 0.545
                anne_yas = U.normal_int(rng, 28.6 + 0.18 * (yil - 2019), 5.2, 17, 46)
                cogul = rng.random() < 0.021
                d.w(T.birth_record).yaz(
                    birth_record_id=bid, birth_date=tarih, neighborhood_id=m["id"],
                    gender="E" if rng.random() < 0.514 else "K",
                    birth_weight_gram=U.normal_int(rng, 3280 if not cogul else 2450, 460, 800, 5200),
                    delivery_type="Sezaryen" if sezaryen else "Normal",
                    mother_age=anne_yas,
                    father_age=min(72, anne_yas + U.normal_int(rng, 3, 4, -6, 22)),
                    birth_order=U.agirlikli(rng, [(1, 44), (2, 33), (3, 15), (4, 5), (5, 3)]),
                    hospital_name=U.agirlikli(rng, [(h, 30 if i < 4 else 10)
                                                    for i, h in enumerate(HASTANELER)]),
                    is_multiple_birth=cogul,
                    registered_at=tarih + dt.timedelta(days=rng.randrange(1, 25)))

    # -------------------------------------------------------------------- olumler
    did = 0
    w.olumler = []
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        kob = 5.35 + 0.06 * (yil - 2019)          # kaba olum hizi (binde)
        if yil == 2020:
            kob *= 1.19
        elif yil == 2021:
            kob *= 1.24
        for m in w.mahalleler:
            n = int(w.nufus(m["id"], yil) / 1000.0 * kob * gun_orani * rng.uniform(0.9, 1.1))
            for _ in range(n):
                did += 1
                tarih = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
                # kis aylarinda olum artisi
                if tarih.month in (12, 1, 2) and rng.random() < 0.18:
                    tarih = tarih
                grup, detaylar = _olum_nedeni(rng, yil, tarih)
                cins = "E" if rng.random() < 0.532 else "K"
                yas = U.normal_int(rng, 74 if cins == "K" else 70, 15, 0, 103)
                if grup == "Kaza ve yaralanma":
                    yas = U.normal_int(rng, 46, 20, 1, 92)
                d.w(T.death_record).yaz(
                    death_record_id=did, death_date=tarih, neighborhood_id=m["id"],
                    gender=cins, age_at_death=yas, age_band=_yas_bandi(yas),
                    cause_group=grup, cause_detail=rng.choice(detaylar),
                    place_of_death=U.agirlikli(rng, [("Hastane", 62), ("Ev", 29),
                                                     ("Bakımevi", 5), ("Diğer", 4)]),
                    burial_permit_no=f"DR-{yil}-{did:06d}",
                    registered_at=tarih + dt.timedelta(days=rng.randrange(0, 4)))
                w.olumler.append((did, tarih, m["id"], yas, cins))

    # ----------------------------------------------------------------------- goc
    gid = 0
    for ay in U.aylar():
        for m in w.mahalleler:
            nfs = w.nufus(m["id"], ay.year)
            for yon, taban in (("Gelen", 0.0072), ("Giden", 0.0069)):
                for kaynak, pay in (("İlçe içi", 0.31), ("İl içi", 0.42),
                                    ("Diğer il", 0.22), ("Yurt dışı", 0.05)):
                    n = int(nfs * taban / 12 * pay * 12 * rng.uniform(0.7, 1.35))
                    gid += 1
                    d.w(T.migration_stat).yaz(
                        migration_stat_id=gid, period_month=ay, neighborhood_id=m["id"],
                        direction=yon, origin_type=kaynak, person_count=n,
                        household_count=max(1, int(n / rng.uniform(2.2, 3.4))))

    # -------------------------------------------------------------------- nikah
    nid = 0
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        n = int(3350 * gun_orani * (1 - 0.018 * (yil - 2019)) * rng.uniform(0.94, 1.06))
        for _ in range(n):
            nid += 1
            tarih = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
            # yaz aylari ve cumartesi yogunlugu
            if tarih.month in (1, 2, 12) and rng.random() < 0.45:
                tarih = dt.date(tarih.year, rng.choice([6, 7, 8, 9]),
                                min(tarih.day, 28))
            gelin_yas = U.normal_int(rng, 25.6 + 0.16 * (yil - 2019), 4.6, 17, 55)
            d.w(T.marriage_record).yaz(
                marriage_record_id=nid, marriage_date=tarih,
                ceremony_hall=U.agirlikli(rng, [(NIKAH_SALONLARI[0], 52), (NIKAH_SALONLARI[1], 24),
                                                (NIKAH_SALONLARI[2], 15), (NIKAH_SALONLARI[3], 9)]),
                neighborhood_id=U.agirlikli(rng, mah_agirlik),
                groom_age=min(70, gelin_yas + U.normal_int(rng, 3, 3, -4, 18)),
                bride_age=gelin_yas,
                groom_education=U.agirlikli(rng, list(zip(EGITIM, EGITIM_AGIRLIK))),
                bride_education=U.agirlikli(rng, list(zip(EGITIM, EGITIM_AGIRLIK))),
                is_first_marriage_groom=rng.random() < 0.89,
                is_first_marriage_bride=rng.random() < 0.91,
                foreign_spouse_flag=rng.random() < 0.047,
                fee_amount=U.para(320 * w.endeks(tarih) * rng.uniform(0.85, 1.3)),
                officiant_name=U.kisi_adi(rng)[0])

    # ------------------------------------------------------------------ bosanma
    bsid = 0
    for yil in U.YILLAR:
        for m in w.mahalleler:
            for band, pay in (("0-1 yıl", 0.09), ("2-5 yıl", 0.31), ("6-10 yıl", 0.22),
                              ("11-15 yıl", 0.15), ("16+ yıl", 0.23)):
                n = int(w.nufus(m["id"], yil) / 1000.0 * 2.05 * pay * rng.uniform(0.8, 1.25))
                if yil == 2026:
                    n = int(n * 0.66)
                bsid += 1
                d.w(T.divorce_stat).yaz(
                    divorce_stat_id=bsid, year=yil, neighborhood_id=m["id"],
                    marriage_duration_band=band, divorce_count=n,
                    child_affected_count=int(n * rng.uniform(0.5, 1.6)))


def _olum_nedeni(rng, yil, tarih):
    agirliklar = []
    for grup, pay, detaylar in OLUM_NEDENI:
        p = pay
        if yil in (2020, 2021):
            if grup == "Enfeksiyon hastalıkları":
                p *= 3.6
            elif grup == "Solunum sistemi hastalıkları":
                p *= 1.35
            elif grup == "Kaza ve yaralanma":
                p *= 0.72
        if tarih.month in (12, 1, 2) and grup in ("Solunum sistemi hastalıkları",
                                                  "Dolaşım sistemi hastalıkları"):
            p *= 1.22
        agirliklar.append(((grup, detaylar), p))
    grup, detaylar = U.agirlikli(rng, agirliklar)
    if grup == "Enfeksiyon hastalıkları" and yil in (2020, 2021):
        detaylar = ["COVID-19"] * 5 + ["Sepsis", "Tüberküloz"]
    return grup, detaylar
