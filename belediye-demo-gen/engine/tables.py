# -*- coding: utf-8 -*-
"""Bahcelievler Belediyesi demo veritabani semasi.

Konvansiyon (mevcut erp_* veritabanlariyla ayni):
  * tablo ve kolon adlari Ingilizce
  * icerik (statu, tur, ad, aciklama) Turkce
  * Turkce isimli analitik view'lar views.py icinde
"""
from .spec import T

MONEY = "numeric(16,2)"

# ===========================================================================
# 1. COGRAFYA / IDARI YAPI
# ===========================================================================

district = T(
    "district", "Ilce kunyesi - Bahcelievler (Istanbul). Tek satirlik referans tablosu.",
    [("district_id", "int", "Ilce kimligi"),
     ("district_name", "text not null", "Ilce adi"),
     ("province_name", "text not null", "Il adi"),
     ("region_name", "text not null", "Bolge (Marmara)"),
     ("area_km2", "numeric(8,2)", "Yuzolcumu (km2)"),
     ("established_year", "int", "Ilce belediyesinin kurulus yili"),
     ("mayor_name", "text", "Belediye baskani (kurgusal)"),
     ("council_seat_count", "int", "Belediye meclisi uye sayisi"),
     ("neighborhood_count", "int", "Mahalle sayisi")],
    pk="district_id")

neighborhood = T(
    "neighborhood", "Bahcelievler'in 11 mahallesi; nufus yogunlugu ve sosyoekonomik profil dahil.",
    [("neighborhood_id", "int", "Mahalle kimligi"),
     ("neighborhood_name", "text not null", "Mahalle adi"),
     ("district_id", "int not null", "Bagli ilce"),
     ("area_km2", "numeric(8,3)", "Mahalle yuzolcumu (km2)"),
     ("street_count", "int", "Cadde/sokak sayisi"),
     ("building_count", "int", "Yaklasik bina sayisi"),
     ("socioeconomic_segment", "text", "Sosyoekonomik segment: Ust, Ust-Orta, Orta, Alt-Orta"),
     ("green_area_m2", "numeric(12,2)", "Toplam yesil alan (m2)"),
     ("mukhtar_name", "text", "Mahalle muhtari (kurgusal)"),
     ("mukhtar_phone", "text", "Muhtarlik telefonu"),
     ("latitude", "numeric(9,6)", "Mahalle merkezi enlem"),
     ("longitude", "numeric(9,6)", "Mahalle merkezi boylam")],
    pk="neighborhood_id",
    fks=[("district_id", "district", "district_id")],
    indexes=["neighborhood_name"])

street = T(
    "street", "Mahallelere bagli cadde ve sokak envanteri.",
    [("street_id", "int", "Sokak kimligi"),
     ("street_name", "text not null", "Cadde/sokak adi"),
     ("street_type", "text", "Tur: Cadde, Sokak, Bulvar, Cikmaz"),
     ("neighborhood_id", "int not null", "Bagli mahalle"),
     ("length_m", "int", "Uzunluk (metre)"),
     ("lane_count", "int", "Serit sayisi"),
     ("surface_type", "text", "Kaplama: Asfalt, Parke, Beton, Stabilize"),
     ("last_pavement_year", "int", "Son ustyapi yenileme yili")],
    pk="street_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["neighborhood_id"])

# ===========================================================================
# 2. NUFUS / DEMOGRAFI
# ===========================================================================

population_stat = T(
    "population_stat", "Mahalle x yil x yas grubu x cinsiyet kirilimindaki yillik nufus (ADNKS benzeri).",
    [("population_stat_id", "int", "Kayit kimligi"),
     ("year", "int not null", "Yil"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("age_band", "text not null", "Yas grubu: 0-4, 5-9, ... 80+"),
     ("gender", "text not null", "Cinsiyet: E (erkek), K (kadin)"),
     ("population", "int not null", "Kisi sayisi"),
     ("citizen_foreign_count", "int", "Icindeki yabanci uyruklu sayisi")],
    pk="population_stat_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["year, neighborhood_id", "age_band"])

household = T(
    "household", "Hane bazli kayit; hane buyuklugu, konut tipi, isinma ve gelir bandi.",
    [("household_id", "int", "Hane kimligi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("street_id", "int", "Sokak"),
     ("member_count", "int not null", "Hanedeki kisi sayisi"),
     ("child_count", "int", "18 yas alti kisi sayisi"),
     ("elderly_count", "int", "65 yas ustu kisi sayisi"),
     ("disabled_count", "int", "Engelli birey sayisi"),
     ("tenure_type", "text", "Konut sahiplik durumu: Ev sahibi, Kiraci, Lojman, Diger"),
     ("dwelling_type", "text", "Konut tipi: Apartman dairesi, Mustakil ev, Rezidans, Gecekondu"),
     ("heating_type", "text", "Isinma: Dogalgaz kombi, Merkezi sistem, Elektrik, Soba"),
     ("income_band", "text", "Aylik hane geliri bandi (TL)"),
     ("registered_at", "date", "Hane kaydinin olusturuldugu tarih")],
    pk="household_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("street_id", "street", "street_id")],
    indexes=["neighborhood_id", "income_band"])

citizen = T(
    "citizen", "Belediye ile etkilesimi olan vatandas kayitlari (basvuru, yardim, uyelik, vergi mukellefi).",
    [("citizen_id", "int", "Vatandas kimligi"),
     ("national_id", "text", "T.C. kimlik numarasi (kurgusal)"),
     ("full_name", "text not null", "Ad soyad"),
     ("gender", "text", "Cinsiyet: E, K"),
     ("birth_date", "date", "Dogum tarihi"),
     ("marital_status", "text", "Medeni hal: Bekar, Evli, Bosanmis, Dul"),
     ("education_level", "text", "Ogrenim durumu: Okur-yazar degil, Ilkokul, Ortaokul, Lise, On lisans, Lisans, Lisansustu"),
     ("employment_status", "text", "Calisma durumu: Calisiyor, Issiz, Emekli, Ogrenci, Ev hanimi, Calisamaz"),
     ("occupation", "text", "Meslek"),
     ("disability_status", "text", "Engel durumu: Yok, Bedensel, Gorme, Isitme, Zihinsel, Sureli hastalik"),
     ("neighborhood_id", "int", "Ikamet mahallesi"),
     ("household_id", "int", "Bagli hane"),
     ("phone", "text", "Cep telefonu"),
     ("email", "text", "E-posta"),
     ("is_household_head", "boolean", "Hane reisi mi"),
     ("registered_at", "date", "Belediye kaydinin acildigi tarih"),
     ("kyk_card_flag", "boolean", "Belediye Kent Kart sahibi mi")],
    pk="citizen_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("household_id", "household", "household_id")],
    indexes=["neighborhood_id", "national_id", "birth_date"])

birth_record = T(
    "birth_record", "Ilcede gerceklesen dogum bildirimleri.",
    [("birth_record_id", "int", "Dogum kayit kimligi"),
     ("birth_date", "date not null", "Dogum tarihi"),
     ("neighborhood_id", "int not null", "Ailenin ikamet mahallesi"),
     ("gender", "text not null", "Bebek cinsiyeti: E, K"),
     ("birth_weight_gram", "int", "Dogum agirligi (gram)"),
     ("delivery_type", "text", "Dogum sekli: Normal, Sezaryen"),
     ("mother_age", "int", "Anne yasi"),
     ("father_age", "int", "Baba yasi"),
     ("birth_order", "int", "Kacinci cocuk"),
     ("hospital_name", "text", "Dogumun yapildigi saglik kurulusu"),
     ("is_multiple_birth", "boolean", "Cogul gebelik mi"),
     ("registered_at", "date", "Kayit tarihi")],
    pk="birth_record_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["birth_date", "neighborhood_id"])

death_record = T(
    "death_record", "Olum kayitlari; olum nedeni, yer ve yas bilgisi ile.",
    [("death_record_id", "int", "Olum kayit kimligi"),
     ("death_date", "date not null", "Olum tarihi"),
     ("neighborhood_id", "int not null", "Ikamet mahallesi"),
     ("gender", "text not null", "Cinsiyet: E, K"),
     ("age_at_death", "int", "Olum yasi"),
     ("age_band", "text", "Yas grubu"),
     ("cause_group", "text", "Olum nedeni ana grubu: Dolasim sistemi, Kanser, Solunum sistemi, Kaza/yaralanma, Enfeksiyon, Sinir sistemi, Diger"),
     ("cause_detail", "text", "Olum nedeni detayi"),
     ("place_of_death", "text", "Olum yeri: Hastane, Ev, Bakimevi, Diger"),
     ("burial_permit_no", "text", "Defin ruhsati numarasi"),
     ("registered_at", "date", "Kayit tarihi")],
    pk="death_record_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["death_date", "cause_group", "neighborhood_id"])

migration_stat = T(
    "migration_stat", "Aylik ic goc hareketi: mahalleye gelen ve mahalleden giden kisi sayilari.",
    [("migration_stat_id", "int", "Kayit kimligi"),
     ("period_month", "date not null", "Ay (ayin ilk gunu)"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("direction", "text not null", "Yon: Gelen, Giden"),
     ("origin_type", "text", "Kaynak/hedef tipi: Ilce ici, Il ici, Diger il, Yurt disi"),
     ("person_count", "int not null", "Kisi sayisi"),
     ("household_count", "int", "Hane sayisi")],
    pk="migration_stat_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["period_month, neighborhood_id"])

marriage_record = T(
    "marriage_record", "Belediye nikah dairesinde kiyilan nikahlar.",
    [("marriage_record_id", "int", "Nikah kayit kimligi"),
     ("marriage_date", "date not null", "Nikah tarihi"),
     ("ceremony_hall", "text", "Nikah salonu"),
     ("neighborhood_id", "int", "Ciftin ikamet mahallesi"),
     ("groom_age", "int", "Damat yasi"),
     ("bride_age", "int", "Gelin yasi"),
     ("groom_education", "text", "Damat ogrenim durumu"),
     ("bride_education", "text", "Gelin ogrenim durumu"),
     ("is_first_marriage_groom", "boolean", "Damat icin ilk evlilik mi"),
     ("is_first_marriage_bride", "boolean", "Gelin icin ilk evlilik mi"),
     ("foreign_spouse_flag", "boolean", "Eslerden biri yabanci uyruklu mu"),
     ("fee_amount", MONEY, "Alinan nikah ucreti (TL)"),
     ("officiant_name", "text", "Nikah memuru")],
    pk="marriage_record_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["marriage_date"])

divorce_stat = T(
    "divorce_stat", "Yillik bosanma istatistikleri (mahalle ve evlilik suresi kirilimi).",
    [("divorce_stat_id", "int", "Kayit kimligi"),
     ("year", "int not null", "Yil"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("marriage_duration_band", "text", "Evlilik suresi bandi: 0-1 yil, 2-5 yil, 6-10 yil, 11-15 yil, 16+ yil"),
     ("divorce_count", "int not null", "Bosanma sayisi"),
     ("child_affected_count", "int", "Etkilenen cocuk sayisi")],
    pk="divorce_stat_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["year, neighborhood_id"])

# ===========================================================================
# 3. ISGUCU / EKONOMI
# ===========================================================================

unemployment_stat = T(
    "unemployment_stat", "Ceyreklik issizlik ve isgucu istatistigi (mahalle x yas x cinsiyet).",
    [("unemployment_stat_id", "int", "Kayit kimligi"),
     ("year", "int not null", "Yil"),
     ("quarter", "int not null", "Ceyrek: 1-4"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("age_band", "text not null", "Yas grubu: 15-24, 25-34, 35-44, 45-54, 55-64"),
     ("gender", "text not null", "Cinsiyet: E, K"),
     ("labor_force", "int not null", "Isgucu (kisi)"),
     ("employed_count", "int not null", "Istihdam edilen kisi"),
     ("unemployed_count", "int not null", "Issiz kisi"),
     ("unemployment_rate", "numeric(6,2)", "Issizlik orani (%)"),
     ("participation_rate", "numeric(6,2)", "Isgucune katilim orani (%)"),
     ("informal_employment_count", "int", "Kayit disi calisan tahmini")],
    pk="unemployment_stat_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["year, quarter, neighborhood_id", "age_band, gender"])

business = T(
    "business", "Ilcede faaliyet gosteren isyeri sicili.",
    [("business_id", "int", "Isyeri kimligi"),
     ("business_name", "text not null", "Isyeri unvani"),
     ("tax_number", "text", "Vergi kimlik numarasi"),
     ("sector", "text not null", "Ana sektor: Perakende, Gida ve icecek, Saglik, Egitim, Insaat, Imalat, Ulastirma, Bilisim, Finans, Kisisel hizmetler, Konaklama, Toptan ticaret"),
     ("nace_code", "text", "NACE faaliyet kodu"),
     ("activity_description", "text", "Faaliyet konusu"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("street_id", "int", "Sokak"),
     ("legal_form", "text", "Hukuki yapi: Sahis, Limited Sirket, Anonim Sirket, Kooperatif, Adi Ortaklik"),
     ("employee_count", "int", "Calisan sayisi"),
     ("open_date", "date", "Faaliyete baslama tarihi"),
     ("close_date", "date", "Kapanis tarihi (acikta ise bos)"),
     ("status", "text", "Durum: Faal, Kapali, Askida, Devredildi"),
     ("area_m2", "int", "Isyeri alani (m2)"),
     ("risk_class", "text", "Ruhsat risk sinifi: Az tehlikeli, Tehlikeli, Cok tehlikeli")],
    pk="business_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("street_id", "street", "street_id")],
    indexes=["neighborhood_id", "sector", "status", "open_date"])

business_license = T(
    "business_license", "Isyeri acma ve calisma ruhsatlari.",
    [("business_license_id", "int", "Ruhsat kimligi"),
     ("business_id", "int not null", "Isyeri"),
     ("license_no", "text", "Ruhsat numarasi"),
     ("license_type", "text", "Ruhsat turu: Sihhi Muessese, Gayrisihhi Muessese 2. Sinif, Gayrisihhi Muessese 3. Sinif, Umuma Acik Istirahat ve Eglence Yeri"),
     ("application_date", "date", "Basvuru tarihi"),
     ("issue_date", "date", "Ruhsat verilis tarihi"),
     ("expiry_date", "date", "Gecerlilik bitis tarihi"),
     ("status", "text", "Durum: Onaylandi, Reddedildi, Beklemede, Iptal edildi"),
     ("fee_amount", MONEY, "Tahsil edilen ruhsat harci (TL)"),
     ("processing_days", "int", "Basvurudan sonuca gecen gun"),
     ("rejection_reason", "text", "Ret gerekcesi")],
    pk="business_license_id",
    fks=[("business_id", "business", "business_id")],
    indexes=["business_id", "issue_date", "status"])

business_inspection = T(
    "business_inspection", "Isyeri denetimleri (zabita, gida, ruhsat uygunluk).",
    [("business_inspection_id", "int", "Denetim kimligi"),
     ("business_id", "int not null", "Denetlenen isyeri"),
     ("inspection_date", "date not null", "Denetim tarihi"),
     ("inspection_type", "text", "Denetim turu: Rutin, Sikayet uzerine, Ruhsat kontrolu, Hijyen, Fiyat etiketi, Gurultu"),
     ("inspector_employee_id", "int", "Denetimi yapan personel"),
     ("result", "text", "Sonuc: Uygun, Uyari verildi, Ceza kesildi, Faaliyetten men, Sure verildi"),
     ("finding_count", "int", "Tespit edilen uygunsuzluk sayisi"),
     ("score", "int", "Denetim puani (0-100)"),
     ("follow_up_required", "boolean", "Takip denetimi gerekiyor mu")],
    pk="business_inspection_id",
    fks=[("business_id", "business", "business_id")],
    indexes=["inspection_date", "business_id", "result"])

vocational_course = T(
    "vocational_course", "Belediye meslek edindirme kurslari (BELMEK tarzi) ve spor/sanat kurslari.",
    [("vocational_course_id", "int", "Kurs kimligi"),
     ("course_name", "text not null", "Kurs adi"),
     ("category", "text", "Kategori: Meslek edindirme, El sanatlari, Bilisim, Yabanci dil, Muzik, Spor, Sinav hazirlik, Kisisel gelisim"),
     ("term", "text", "Donem: 2024-Guz gibi"),
     ("start_date", "date", "Baslangic tarihi"),
     ("end_date", "date", "Bitis tarihi"),
     ("neighborhood_id", "int", "Kursun verildigi mahalle"),
     ("venue_name", "text", "Kurs merkezi adi"),
     ("instructor_name", "text", "Egitmen"),
     ("capacity", "int", "Kontenjan"),
     ("total_hours", "int", "Toplam ders saati"),
     ("fee_amount", MONEY, "Kurs ucreti (TL, cogu ucretsiz)"),
     ("cost_amount", MONEY, "Belediyeye maliyeti (TL)")],
    pk="vocational_course_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["start_date", "category"])

course_enrollment = T(
    "course_enrollment", "Kurs kayitlari ve tamamlama/sertifika durumu.",
    [("course_enrollment_id", "int", "Kayit kimligi"),
     ("vocational_course_id", "int not null", "Kurs"),
     ("citizen_id", "int", "Kursiyer"),
     ("enrollment_date", "date", "Kayit tarihi"),
     ("attendance_rate", "numeric(5,2)", "Devam orani (%)"),
     ("status", "text", "Durum: Devam ediyor, Tamamladi, Birakti, Kayit iptal"),
     ("certificate_issued", "boolean", "Sertifika verildi mi"),
     ("employed_after_course", "boolean", "Kurs sonrasi ise yerlesti mi"),
     ("satisfaction_score", "int", "Memnuniyet puani (1-5)")],
    pk="course_enrollment_id",
    fks=[("vocational_course_id", "vocational_course", "vocational_course_id"),
         ("citizen_id", "citizen", "citizen_id")],
    indexes=["vocational_course_id", "citizen_id", "status"])

# ===========================================================================
# 4. EMLAK / YEREL VERGI
# ===========================================================================

building = T(
    "building", "Bina envanteri (yapi kayit, kat sayisi, deprem risk durumu).",
    [("building_id", "int", "Bina kimligi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("street_id", "int", "Sokak"),
     ("building_no", "text", "Kapi numarasi"),
     ("construction_year", "int", "Yapim yili"),
     ("floor_count", "int", "Kat sayisi"),
     ("unit_count", "int", "Bagimsiz bolum sayisi"),
     ("structure_type", "text", "Tasiyici sistem: Betonarme, Yigma, Celik, Prefabrik"),
     ("usage_type", "text", "Kullanim: Konut, Ticari, Karma, Kamu, Egitim, Saglik, Ibadet"),
     ("has_occupancy_permit", "boolean", "Yapi kullanma izni (iskan) var mi"),
     ("has_elevator", "boolean", "Asansor var mi"),
     ("earthquake_risk_class", "text", "Deprem risk sinifi: Dusuk, Orta, Yuksek, Acil riskli"),
     ("urban_renewal_status", "text", "Kentsel donusum durumu: Kapsam disi, Basvuru yapildi, Riskli ilan edildi, Yikildi, Yeniden yapildi"),
     ("total_area_m2", "numeric(12,2)", "Toplam insaat alani (m2)")],
    pk="building_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("street_id", "street", "street_id")],
    indexes=["neighborhood_id", "earthquake_risk_class", "construction_year"])

property_unit = T(
    "property_unit", "Bagimsiz bolum (daire, dukkan, ofis) envanteri.",
    [("property_unit_id", "int", "Bagimsiz bolum kimligi"),
     ("building_id", "int not null", "Bina"),
     ("unit_no", "text", "Bagimsiz bolum numarasi"),
     ("floor_no", "int", "Bulundugu kat"),
     ("unit_type", "text", "Tur: Mesken, Isyeri, Depo, Otopark, Arsa"),
     ("gross_area_m2", "numeric(10,2)", "Brut alan (m2)"),
     ("room_layout", "text", "Oda duzeni: 1+0, 1+1, 2+1, 3+1, 4+1, Dukkan"),
     ("heating_type", "text", "Isinma tipi"),
     ("current_value_try", MONEY, "Guncel emlak rayic degeri (TL)"),
     ("owner_citizen_id", "int", "Malik (vatandas)"),
     ("is_rented", "boolean", "Kirada mi")],
    pk="property_unit_id",
    fks=[("building_id", "building", "building_id"),
         ("owner_citizen_id", "citizen", "citizen_id")],
    indexes=["building_id", "unit_type", "owner_citizen_id"])

property_declaration = T(
    "property_declaration", "Emlak vergisi beyannameleri.",
    [("property_declaration_id", "int", "Beyan kimligi"),
     ("property_unit_id", "int not null", "Bagimsiz bolum"),
     ("citizen_id", "int", "Mukellef"),
     ("declaration_date", "date", "Beyan tarihi"),
     ("declaration_type", "text", "Beyan turu: Yeni edinim, Degisiklik, Devir, Miras"),
     ("declared_value_try", MONEY, "Beyan edilen deger (TL)"),
     ("tax_class", "text", "Vergi turu: Bina - Mesken, Bina - Isyeri, Arsa, Arazi"),
     ("exemption_type", "text", "Muafiyet: Yok, Tek konut emekli, Sehit yakini, Engelli, Issiz"),
     ("first_tax_year", "int", "Vergiye tabi ilk yil"),
     ("is_active", "boolean", "Beyan hala gecerli mi")],
    pk="property_declaration_id",
    fks=[("property_unit_id", "property_unit", "property_unit_id"),
         ("citizen_id", "citizen", "citizen_id")],
    indexes=["property_unit_id", "citizen_id", "declaration_date"])

property_tax_assessment = T(
    "property_tax_assessment", "Emlak vergisi yillik tahakkuklari (2 taksit).",
    [("property_tax_assessment_id", "bigint", "Tahakkuk kimligi"),
     ("property_declaration_id", "int not null", "Beyan"),
     ("citizen_id", "int", "Mukellef"),
     ("neighborhood_id", "int", "Mahalle (raporlama kolayligi icin)"),
     ("tax_year", "int not null", "Vergi yili"),
     ("installment_no", "int", "Taksit no: 1 (Mayis), 2 (Kasim)"),
     ("due_date", "date", "Son odeme tarihi"),
     ("assessed_value_try", MONEY, "Matrah (TL)"),
     ("tax_rate", "numeric(6,4)", "Vergi orani (binde)"),
     ("assessed_amount", MONEY, "Tahakkuk eden vergi (TL)"),
     ("penalty_amount", MONEY, "Gecikme zammi (TL)"),
     ("total_due", MONEY, "Toplam borc (TL)"),
     ("status", "text", "Durum: Odendi, Kismi odendi, Odenmedi, Yapilandirildi, Terkin edildi")],
    pk="property_tax_assessment_id",
    fks=[("property_declaration_id", "property_declaration", "property_declaration_id"),
         ("citizen_id", "citizen", "citizen_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["tax_year", "citizen_id", "status", "neighborhood_id, tax_year"])

property_tax_payment = T(
    "property_tax_payment", "Emlak vergisi tahsilatlari.",
    [("property_tax_payment_id", "bigint", "Tahsilat kimligi"),
     ("property_tax_assessment_id", "bigint not null", "Tahakkuk"),
     ("citizen_id", "int", "Mukellef"),
     ("payment_date", "date not null", "Odeme tarihi"),
     ("amount", MONEY, "Odenen tutar (TL)"),
     ("channel", "text", "Tahsilat kanali: Belediye veznesi, Internet, Mobil uygulama, Banka, PTT, Kredi kartı"),
     ("is_late", "boolean", "Vadesinden sonra mi odendi"),
     ("late_days", "int", "Gecikme gun sayisi")],
    pk="property_tax_payment_id",
    fks=[("property_tax_assessment_id", "property_tax_assessment", "property_tax_assessment_id"),
         ("citizen_id", "citizen", "citizen_id")],
    indexes=["payment_date", "citizen_id"])

environmental_tax = T(
    "environmental_tax", "Cevre temizlik vergisi (CTV) tahakkuk ve tahsilati - isyeri ve mesken.",
    [("environmental_tax_id", "bigint", "CTV kayit kimligi"),
     ("tax_year", "int not null", "Vergi yili"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("business_id", "int", "Isyeri (mesken CTV'sinde bos)"),
     ("property_unit_id", "int", "Bagimsiz bolum"),
     ("taxpayer_type", "text", "Mukellef tipi: Isyeri, Mesken"),
     ("tariff_group", "text", "Tarife grubu: 1. Grup ... 7. Grup"),
     ("assessed_amount", MONEY, "Tahakkuk eden CTV (TL)"),
     ("collected_amount", MONEY, "Tahsil edilen tutar (TL)"),
     ("status", "text", "Durum: Odendi, Kismi odendi, Odenmedi")],
    pk="environmental_tax_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("business_id", "business", "business_id")],
    indexes=["tax_year, neighborhood_id", "business_id"])

advertisement_tax = T(
    "advertisement_tax", "Ilan ve reklam vergisi kayitlari (tabela, bilboard, arac reklami).",
    [("advertisement_tax_id", "int", "Kayit kimligi"),
     ("tax_year", "int not null", "Vergi yili"),
     ("business_id", "int", "Mukellef isyeri"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("ad_type", "text", "Ilan turu: Isik yansitmali tabela, Isiksiz tabela, Bez afis, Bilboard, Arac uzeri reklam, Dijital ekran"),
     ("area_m2", "numeric(8,2)", "Ilan alani (m2)"),
     ("unit_rate", MONEY, "Birim tarife (TL/m2)"),
     ("assessed_amount", MONEY, "Tahakkuk eden vergi (TL)"),
     ("collected_amount", MONEY, "Tahsil edilen tutar (TL)"),
     ("permit_status", "text", "Izin durumu: Izinli, Izinsiz, Kaldirildi")],
    pk="advertisement_tax_id",
    fks=[("business_id", "business", "business_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["tax_year", "neighborhood_id"])

# ===========================================================================
# 5. MALI ISLER / BUTCE (Analitik Butce Siniflandirmasi)
# ===========================================================================

fiscal_year = T(
    "fiscal_year", "Mali yil kunyesi: butce buyuklugu, gerceklesme ve makro varsayimlar.",
    [("fiscal_year_id", "int", "Mali yil kimligi"),
     ("year", "int not null", "Yil"),
     ("budget_total_try", MONEY, "Baslangic butce odenegi (TL)"),
     ("revised_budget_try", MONEY, "Revize butce odenegi (TL)"),
     ("realized_revenue_try", MONEY, "Gerceklesen gelir (TL)"),
     ("realized_expense_try", MONEY, "Gerceklesen gider (TL)"),
     ("inflation_rate", "numeric(6,2)", "Yillik TUFE (%)"),
     ("status", "text", "Durum: Kesin hesap onayli, Yil ici, Tahmin"),
     ("council_approval_date", "date", "Meclis butce onay tarihi")],
    pk="fiscal_year_id",
    indexes=["year"])

functional_code = T(
    "functional_code", "Butce fonksiyonel siniflandirma kodlari (hizmet alani).",
    [("functional_code_id", "int", "Kod kimligi"),
     ("code", "text not null", "Fonksiyonel kod (orn. 06)"),
     ("name", "text not null", "Fonksiyon adi (orn. Iskan ve toplum refahi)"),
     ("sub_code", "text", "Alt kod"),
     ("sub_name", "text", "Alt fonksiyon adi")],
    pk="functional_code_id")

economic_code = T(
    "economic_code", "Butce ekonomik siniflandirma kodlari; gelir ve gider tarafi.",
    [("economic_code_id", "int", "Kod kimligi"),
     ("direction", "text not null", "Yon: Gelir, Gider"),
     ("code", "text not null", "Ekonomik kod (orn. 03)"),
     ("name", "text not null", "Ekonomik kod adi (orn. Mal ve hizmet alim giderleri)"),
     ("sub_code", "text", "Alt kod"),
     ("sub_name", "text", "Alt kalem adi")],
    pk="economic_code_id",
    indexes=["direction"])

budget_line = T(
    "budget_line", "Yillik butce kalemleri: mudurluk x fonksiyon x ekonomik kod bazinda odenek ve gerceklesme.",
    [("budget_line_id", "int", "Butce kalem kimligi"),
     ("year", "int not null", "Mali yil"),
     ("directorate_id", "int", "Harcama birimi (mudurluk)"),
     ("functional_code_id", "int", "Fonksiyonel kod"),
     ("economic_code_id", "int not null", "Ekonomik kod"),
     ("direction", "text not null", "Yon: Gelir, Gider"),
     ("initial_appropriation", MONEY, "Baslangic odenegi (TL)"),
     ("transfers_in", MONEY, "Aktarma ile eklenen (TL)"),
     ("transfers_out", MONEY, "Aktarma ile dusulen (TL)"),
     ("revised_appropriation", MONEY, "Revize odenek (TL)"),
     ("realized_amount", MONEY, "Gerceklesen tutar (TL)"),
     ("realization_rate", "numeric(6,2)", "Gerceklesme orani (%)")],
    pk="budget_line_id",
    fks=[("functional_code_id", "functional_code", "functional_code_id"),
         ("economic_code_id", "economic_code", "economic_code_id")],
    indexes=["year, direction", "directorate_id"])

revenue_transaction = T(
    "revenue_transaction", "Gelir hareketleri: vergi, harc, kira, Iller Bankasi payi, bagis vb.",
    [("revenue_transaction_id", "bigint", "Gelir hareket kimligi"),
     ("transaction_date", "date not null", "Tahsilat tarihi"),
     ("year", "int not null", "Mali yil"),
     ("economic_code_id", "int", "Gelir ekonomik kodu"),
     ("revenue_type", "text not null", "Gelir turu: Emlak vergisi, Cevre temizlik vergisi, Ilan ve reklam vergisi, Isyeri ruhsat harci, Insaat ruhsat harci, Kayit ve suret harci, Otopark geliri, Kira geliri, Iller Bankasi payi, Idari para cezasi, Sosyal tesis geliri, Bagis ve yardim, Arsa satisi, Diger gelirler"),
     ("neighborhood_id", "int", "Ilgili mahalle (varsa)"),
     ("directorate_id", "int", "Geliri tahsil eden mudurluk"),
     ("amount", MONEY, "Tutar (TL)"),
     ("channel", "text", "Tahsilat kanali"),
     ("document_no", "text", "Tahsilat makbuz numarasi"),
     ("description", "text", "Aciklama")],
    pk="revenue_transaction_id",
    fks=[("economic_code_id", "economic_code", "economic_code_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["transaction_date", "revenue_type", "year"])

expense_transaction = T(
    "expense_transaction", "Gider hareketleri: personel, mal ve hizmet alimi, sermaye, transfer.",
    [("expense_transaction_id", "bigint", "Gider hareket kimligi"),
     ("transaction_date", "date not null", "Muhasebe tarihi"),
     ("year", "int not null", "Mali yil"),
     ("directorate_id", "int", "Harcama birimi"),
     ("functional_code_id", "int", "Fonksiyonel kod"),
     ("economic_code_id", "int", "Ekonomik kod"),
     ("expense_type", "text not null", "Gider turu: Personel gideri, SGK devlet primi, Mal ve malzeme alimi, Hizmet alimi, Enerji ve yakit, Kira gideri, Bakim onarim, Yapim isi, Makine techizat alimi, Sosyal yardim, Faiz gideri, Vergi ve harc, Diger cari"),
     ("supplier_id", "int", "Tedarikci (varsa)"),
     ("contract_id", "int", "Sozlesme (varsa)"),
     ("neighborhood_id", "int", "Harcamanin yapildigi mahalle (varsa)"),
     ("amount", MONEY, "Tutar (TL, KDV haric)"),
     ("vat_amount", MONEY, "KDV tutari (TL)"),
     ("total_amount", MONEY, "Toplam tutar (TL)"),
     ("document_no", "text", "Muhasebe fis numarasi"),
     ("description", "text", "Aciklama")],
    pk="expense_transaction_id",
    fks=[("functional_code_id", "functional_code", "functional_code_id"),
         ("economic_code_id", "economic_code", "economic_code_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["transaction_date", "expense_type", "year", "directorate_id", "supplier_id"])

supplier = T(
    "supplier", "Belediyeye mal ve hizmet saglayan yukleniciler.",
    [("supplier_id", "int", "Tedarikci kimligi"),
     ("supplier_name", "text not null", "Firma unvani"),
     ("tax_number", "text", "Vergi kimlik numarasi"),
     ("category", "text", "Kategori: Insaat ve taahhut, Temizlik hizmeti, Guvenlik hizmeti, Arac kiralama, Gida, Akaryakit, Bilisim, Kirtasiye, Peyzaj, Danismanlik, Enerji, Saglik malzemesi"),
     ("city", "text", "Sehir"),
     ("is_local", "boolean", "Ilce icinde mi"),
     ("first_contract_date", "date", "Ilk sozlesme tarihi"),
     ("blacklisted", "boolean", "Yasakli mi (ihalelere katilim yasagi)"),
     ("contact_person", "text", "Yetkili kisi"),
     ("phone", "text", "Telefon"),
     ("iban", "text", "IBAN")],
    pk="supplier_id",
    indexes=["category", "supplier_name"])

tender = T(
    "tender", "Kamu ihaleleri (4734 sayili Kanun) ve dogrudan temin kayitlari.",
    [("tender_id", "int", "Ihale kimligi"),
     ("tender_no", "text", "Ihale kayit numarasi (IKN)"),
     ("title", "text not null", "Ihale konusu"),
     ("directorate_id", "int", "Ihaleyi yapan mudurluk"),
     ("procurement_type", "text", "Ihale usulu: Acik ihale, Belli istekliler arasinda, Pazarlik usulu, Dogrudan temin"),
     ("work_type", "text", "Is turu: Yapim isi, Mal alimi, Hizmet alimi, Danismanlik"),
     ("announcement_date", "date", "Ilan tarihi"),
     ("tender_date", "date", "Ihale tarihi"),
     ("estimated_cost", MONEY, "Yaklasik maliyet (TL)"),
     ("winning_bid", MONEY, "Sozlesme bedeli (TL)"),
     ("bidder_count", "int", "Katilan istekli sayisi"),
     ("winner_supplier_id", "int", "Kazanan yuklenici"),
     ("discount_rate", "numeric(6,2)", "Yaklasik maliyete gore kirim orani (%)"),
     ("status", "text", "Durum: Sonuclandi, Iptal edildi, Itiraz surecinde, Devam ediyor")],
    pk="tender_id",
    fks=[("winner_supplier_id", "supplier", "supplier_id")],
    indexes=["tender_date", "procurement_type", "work_type"])

contract = T(
    "contract", "Ihale sonrasi imzalanan sozlesmeler ve hakedis takibi.",
    [("contract_id", "int", "Sozlesme kimligi"),
     ("tender_id", "int", "Ihale"),
     ("supplier_id", "int not null", "Yuklenici"),
     ("directorate_id", "int", "Sorumlu mudurluk"),
     ("contract_no", "text", "Sozlesme numarasi"),
     ("subject", "text", "Sozlesme konusu"),
     ("start_date", "date", "Ise baslama tarihi"),
     ("end_date", "date", "Sozlesme bitis tarihi"),
     ("contract_amount", MONEY, "Sozlesme bedeli (TL)"),
     ("price_increase_amount", MONEY, "Fiyat farki / is artisi (TL)"),
     ("paid_to_date", MONEY, "Bugune kadar odenen (TL)"),
     ("completion_rate", "numeric(6,2)", "Fiziki gerceklesme orani (%)"),
     ("penalty_applied", MONEY, "Uygulanan gecikme cezasi (TL)"),
     ("status", "text", "Durum: Devam ediyor, Tamamlandi, Feshedildi, Tasfiye edildi"),
     ("guarantee_amount", MONEY, "Kesin teminat (TL)")],
    pk="contract_id",
    fks=[("tender_id", "tender", "tender_id"),
         ("supplier_id", "supplier", "supplier_id")],
    indexes=["supplier_id", "start_date", "status"])

payment_order = T(
    "payment_order", "Odeme emri belgeleri (tedarikci ve hakedis odemeleri).",
    [("payment_order_id", "bigint", "Odeme emri kimligi"),
     ("order_no", "text", "Odeme emri numarasi"),
     ("order_date", "date not null", "Duzenleme tarihi"),
     ("payment_date", "date", "Odeme tarihi"),
     ("supplier_id", "int", "Odeme yapilan taraf"),
     ("contract_id", "int", "Ilgili sozlesme"),
     ("directorate_id", "int", "Harcama birimi"),
     ("gross_amount", MONEY, "Brut tutar (TL)"),
     ("withholding_amount", MONEY, "Stopaj ve kesintiler (TL)"),
     ("net_amount", MONEY, "Net odenen (TL)"),
     ("status", "text", "Durum: Odendi, Beklemede, Iade edildi, Iptal"),
     ("delay_days", "int", "Duzenleme ile odeme arasindaki gun")],
    pk="payment_order_id",
    fks=[("supplier_id", "supplier", "supplier_id"),
         ("contract_id", "contract", "contract_id")],
    indexes=["order_date", "supplier_id", "status"])

municipal_loan = T(
    "municipal_loan", "Belediyenin kredi ve borc stoku (Iller Bankasi, ticari banka).",
    [("municipal_loan_id", "int", "Kredi kimligi"),
     ("lender", "text", "Kredi veren: Iller Bankasi A.S., Ziraat Bankasi, Halkbank, Vakifbank, Yatirim ve kalkinma"),
     ("purpose", "text", "Kullanim amaci"),
     ("start_date", "date", "Kullandirim tarihi"),
     ("maturity_date", "date", "Vade sonu"),
     ("principal_amount", MONEY, "Anapara (TL)"),
     ("interest_rate", "numeric(6,2)", "Faiz orani (%)"),
     ("outstanding_amount", MONEY, "Kalan bakiye (TL)"),
     ("annual_installment", MONEY, "Yillik taksit tutari (TL)"),
     ("status", "text", "Durum: Devam ediyor, Kapandi, Yapilandirildi")],
    pk="municipal_loan_id")

# ===========================================================================
# 6. INSAN KAYNAKLARI / PERSONEL
# ===========================================================================

directorate = T(
    "directorate", "Belediye mudurlukleri ve baglı harcama birimleri.",
    [("directorate_id", "int", "Mudurluk kimligi"),
     ("directorate_name", "text not null", "Mudurluk adi"),
     ("deputy_mayor_area", "text", "Bagli baskan yardimciligi"),
     ("service_group", "text", "Hizmet grubu: Destek hizmetleri, Mali hizmetler, Teknik hizmetler, Sosyal hizmetler, Kentsel hizmetler, Denetim"),
     ("headcount_budget", "int", "Norm kadro sayisi"),
     ("cost_center_code", "text", "Kurumsal kod"),
     ("manager_name", "text", "Mudur (kurgusal)"),
     ("building_name", "text", "Hizmet binasi")],
    pk="directorate_id",
    indexes=["directorate_name"])

job_title = T(
    "job_title", "Kadro ve unvan tanimlari.",
    [("job_title_id", "int", "Unvan kimligi"),
     ("title_name", "text not null", "Unvan adi"),
     ("staff_class", "text", "Hizmet sinifi: Genel Idare Hizmetleri, Teknik Hizmetler, Saglik Hizmetleri, Avukatlik Hizmetleri, Yardimci Hizmetler"),
     ("employment_type", "text", "Istihdam turu: Memur, Sozlesmeli personel, Surekli isci, Sirket personeli"),
     ("grade_min", "int", "En dusuk derece"),
     ("grade_max", "int", "En yuksek derece"),
     ("base_salary_index", "numeric(8,2)", "Maas endeksi (gosterge benzeri)")],
    pk="job_title_id")

employee = T(
    "employee", "Belediye personeli (memur, sozlesmeli, isci, sirket personeli).",
    [("employee_id", "int", "Personel kimligi"),
     ("employee_no", "text", "Sicil numarasi"),
     ("full_name", "text not null", "Ad soyad"),
     ("national_id", "text", "T.C. kimlik numarasi (kurgusal)"),
     ("gender", "text", "Cinsiyet: E, K"),
     ("birth_date", "date", "Dogum tarihi"),
     ("directorate_id", "int not null", "Bagli mudurluk"),
     ("job_title_id", "int not null", "Unvan"),
     ("employment_type", "text", "Istihdam turu: Memur, Sozlesmeli personel, Surekli isci, Sirket personeli"),
     ("grade", "int", "Derece"),
     ("step", "int", "Kademe"),
     ("hire_date", "date not null", "Ise giris tarihi"),
     ("termination_date", "date", "Ayrilis tarihi (calisanlar icin bos)"),
     ("termination_reason", "text", "Ayrilis nedeni: Emeklilik, Istifa, Nakil, Sozlesme feshi, Vefat"),
     ("status", "text", "Durum: Calisiyor, Ayrildi, Ucretsiz izinde, Askerlikte"),
     ("education_level", "text", "Ogrenim durumu"),
     ("union_member", "boolean", "Sendika uyesi mi"),
     ("disability_quota", "boolean", "Engelli kadrosunda mi"),
     ("work_location", "text", "Calisma yeri"),
     ("neighborhood_id", "int", "Ikamet mahallesi"),
     ("phone", "text", "Telefon"),
     ("iban", "text", "Maas hesabi IBAN")],
    pk="employee_id",
    fks=[("directorate_id", "directorate", "directorate_id"),
         ("job_title_id", "job_title", "job_title_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["directorate_id", "employment_type", "status", "hire_date"])

payroll = T(
    "payroll", "Aylik bordro: brut, kesintiler, net ve isveren maliyeti.",
    [("payroll_id", "bigint", "Bordro kimligi"),
     ("employee_id", "int not null", "Personel"),
     ("period_month", "date not null", "Bordro ayi (ayin ilk gunu)"),
     ("year", "int not null", "Yil"),
     ("directorate_id", "int", "Mudurluk (raporlama icin)"),
     ("employment_type", "text", "Istihdam turu"),
     ("base_salary", MONEY, "Taban / cıplak maas (TL)"),
     ("seniority_pay", MONEY, "Kidem/hizmet tazminati odemesi (TL)"),
     ("additional_payment", MONEY, "Ek odeme ve tazminatlar (TL)"),
     ("overtime_pay", MONEY, "Fazla mesai ucreti (TL)"),
     ("family_allowance", MONEY, "Aile ve cocuk yardimi (TL)"),
     ("meal_transport_allowance", MONEY, "Yemek ve yol yardimi (TL)"),
     ("bonus", MONEY, "Ikramiye / sosyal denge tazminati (TL)"),
     ("gross_pay", MONEY, "Brut ucret (TL)"),
     ("income_tax", MONEY, "Gelir vergisi (TL)"),
     ("stamp_tax", MONEY, "Damga vergisi (TL)"),
     ("social_security_employee", MONEY, "SGK isci payi (TL)"),
     ("union_due", MONEY, "Sendika aidati (TL)"),
     ("other_deductions", MONEY, "Diger kesintiler (icra, kefalet) (TL)"),
     ("net_pay", MONEY, "Net odenen (TL)"),
     ("social_security_employer", MONEY, "SGK isveren payi (TL)"),
     ("employer_cost", MONEY, "Toplam isveren maliyeti (TL)"),
     ("worked_days", "int", "Calisilan gun")],
    pk="payroll_id",
    fks=[("employee_id", "employee", "employee_id"),
         ("directorate_id", "directorate", "directorate_id")],
    indexes=["period_month", "employee_id", "year, directorate_id"])

leave_record = T(
    "leave_record", "Personel izin kayitlari.",
    [("leave_record_id", "int", "Izin kimligi"),
     ("employee_id", "int not null", "Personel"),
     ("leave_type", "text", "Izin turu: Yillik izin, Mazeret izni, Saglik raporu, Dogum izni, Ucretsiz izin, Refakat izni, Idari izin"),
     ("start_date", "date not null", "Baslangic"),
     ("end_date", "date", "Bitis"),
     ("day_count", "int", "Gun sayisi"),
     ("approved_by", "text", "Onaylayan"),
     ("status", "text", "Durum: Onaylandi, Reddedildi, Iptal edildi")],
    pk="leave_record_id",
    fks=[("employee_id", "employee", "employee_id")],
    indexes=["employee_id", "start_date", "leave_type"])

overtime_record = T(
    "overtime_record", "Fazla mesai kayitlari (kar, bayram, etkinlik, acil durum).",
    [("overtime_record_id", "bigint", "Mesai kimligi"),
     ("employee_id", "int not null", "Personel"),
     ("work_date", "date not null", "Mesai tarihi"),
     ("directorate_id", "int", "Mudurluk"),
     ("hours", "numeric(6,2)", "Mesai saati"),
     ("reason", "text", "Gerekce: Kar mucadelesi, Bayram nobeti, Etkinlik, Acil mudahale, Yogunluk, Secim gorevi"),
     ("hourly_rate", MONEY, "Saatlik mesai ucreti (TL)"),
     ("amount", MONEY, "Odenen tutar (TL)"),
     ("is_holiday", "boolean", "Resmi tatil mi")],
    pk="overtime_record_id",
    fks=[("employee_id", "employee", "employee_id"),
         ("directorate_id", "directorate", "directorate_id")],
    indexes=["work_date", "employee_id"])

training_record = T(
    "training_record", "Personel hizmet ici egitimleri.",
    [("training_record_id", "int", "Egitim kayit kimligi"),
     ("employee_id", "int not null", "Personel"),
     ("training_name", "text", "Egitim adi"),
     ("training_category", "text", "Kategori: Is sagligi ve guvenligi, Mevzuat, Teknik, Kisisel gelisim, Bilisim, Halkla iliskiler, Yonetim"),
     ("training_date", "date not null", "Egitim tarihi"),
     ("hours", "int", "Sure (saat)"),
     ("provider", "text", "Egitim saglayici"),
     ("cost_amount", MONEY, "Kisi basi maliyet (TL)"),
     ("exam_score", "int", "Sinav puani"),
     ("certificate_issued", "boolean", "Sertifika verildi mi")],
    pk="training_record_id",
    fks=[("employee_id", "employee", "employee_id")],
    indexes=["training_date", "employee_id"])

performance_review = T(
    "performance_review", "Yillik personel performans degerlendirmeleri.",
    [("performance_review_id", "int", "Degerlendirme kimligi"),
     ("employee_id", "int not null", "Personel"),
     ("year", "int not null", "Degerlendirme yili"),
     ("directorate_id", "int", "Mudurluk"),
     ("score", "numeric(5,2)", "Genel puan (0-100)"),
     ("grade", "text", "Not: Cok iyi, Iyi, Orta, Gelistirilmeli"),
     ("attendance_score", "numeric(5,2)", "Devam-devamsizlik puani"),
     ("citizen_feedback_score", "numeric(5,2)", "Vatandas geri bildirim puani"),
     ("promotion_recommended", "boolean", "Terfi onerildi mi")],
    pk="performance_review_id",
    fks=[("employee_id", "employee", "employee_id")],
    indexes=["year, employee_id"])

# ===========================================================================
# 7. IMAR VE SEHIRCILIK
# ===========================================================================

zoning_application = T(
    "zoning_application", "Imar ve sehircilik basvurulari (imar durumu, tadilat, plan tadili).",
    [("zoning_application_id", "int", "Basvuru kimligi"),
     ("application_no", "text", "Basvuru numarasi"),
     ("application_date", "date not null", "Basvuru tarihi"),
     ("application_type", "text", "Basvuru turu: Imar durumu belgesi, Yeni yapi ruhsati, Tadilat ruhsati, Yikim ruhsati, Plan tadilati, Ifraz-tevhid, Kot kesit, Yapi kayit belgesi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("building_id", "int", "Ilgili bina"),
     ("parcel_no", "text", "Ada/parsel"),
     ("applicant_citizen_id", "int", "Basvuru sahibi"),
     ("applicant_type", "text", "Basvuran: Malik, Muteahhit, Vekil, Kamu kurumu"),
     ("result_date", "date", "Sonuclanma tarihi"),
     ("status", "text", "Durum: Onaylandi, Reddedildi, Eksik evrak, Incelemede, Iptal"),
     ("processing_days", "int", "Sonuclanma suresi (gun)"),
     ("fee_amount", MONEY, "Alinan harc (TL)"),
     ("rejection_reason", "text", "Ret gerekcesi")],
    pk="zoning_application_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("building_id", "building", "building_id"),
         ("applicant_citizen_id", "citizen", "citizen_id")],
    indexes=["application_date", "neighborhood_id", "status", "application_type"])

building_permit = T(
    "building_permit", "Yapi ruhsatlari.",
    [("building_permit_id", "int", "Ruhsat kimligi"),
     ("zoning_application_id", "int", "Ilgili basvuru"),
     ("permit_no", "text", "Ruhsat numarasi"),
     ("issue_date", "date not null", "Ruhsat tarihi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("building_id", "int", "Bina"),
     ("permit_type", "text", "Ruhsat turu: Yeni yapi, Ilave, Tadilat, Yenileme, Isim degisikligi"),
     ("usage_class", "text", "Yapi kullanim sinifi: Konut, Ticari, Karma, Sanayi, Egitim, Saglik"),
     ("floor_count", "int", "Kat sayisi"),
     ("unit_count", "int", "Bagimsiz bolum sayisi"),
     ("construction_area_m2", "numeric(12,2)", "Insaat alani (m2)"),
     ("contractor_name", "text", "Muteahhit"),
     ("estimated_cost", MONEY, "Yaklasik yapi maliyeti (TL)"),
     ("permit_fee", MONEY, "Ruhsat harci (TL)"),
     ("status", "text", "Durum: Gecerli, Suresi doldu, Iptal edildi, Iskan alindi")],
    pk="building_permit_id",
    fks=[("zoning_application_id", "zoning_application", "zoning_application_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("building_id", "building", "building_id")],
    indexes=["issue_date", "neighborhood_id", "usage_class"])

occupancy_permit = T(
    "occupancy_permit", "Yapi kullanma izin belgeleri (iskan).",
    [("occupancy_permit_id", "int", "Iskan kimligi"),
     ("building_permit_id", "int", "Yapi ruhsati"),
     ("permit_no", "text", "Belge numarasi"),
     ("issue_date", "date not null", "Belge tarihi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("building_id", "int", "Bina"),
     ("unit_count", "int", "Iskan alan bagimsiz bolum sayisi"),
     ("construction_area_m2", "numeric(12,2)", "Insaat alani (m2)"),
     ("fee_amount", MONEY, "Alinan harc (TL)"),
     ("elapsed_months_from_permit", "int", "Ruhsattan iskana gecen ay")],
    pk="occupancy_permit_id",
    fks=[("building_permit_id", "building_permit", "building_permit_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["issue_date", "neighborhood_id"])

earthquake_risk_survey = T(
    "earthquake_risk_survey", "Bina deprem risk tespit ve kentsel donusum surec kayitlari.",
    [("earthquake_risk_survey_id", "int", "Tespit kimligi"),
     ("building_id", "int not null", "Bina"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("survey_date", "date not null", "Tespit tarihi"),
     ("survey_firm", "text", "Lisansli tespit kurulusu"),
     ("risk_result", "text", "Sonuc: Riskli, Risksiz, Guclendirme onerildi, Veri yetersiz"),
     ("concrete_strength_mpa", "numeric(6,2)", "Beton basinc dayanimi (MPa)"),
     ("rebar_condition", "text", "Donati durumu: Iyi, Orta, Kotu"),
     ("recommended_action", "text", "Onerilen islem: Yikim, Guclendirme, Islem yok, Detayli inceleme"),
     ("demolition_date", "date", "Yikim tarihi (varsa)"),
     ("rental_aid_granted", "boolean", "Kira yardimi verildi mi"),
     ("rental_aid_amount", MONEY, "Toplam kira yardimi (TL)")],
    pk="earthquake_risk_survey_id",
    fks=[("building_id", "building", "building_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["survey_date", "risk_result", "neighborhood_id"])

# ===========================================================================
# 8. ZABITA VE DENETIM
# ===========================================================================

municipal_police_action = T(
    "municipal_police_action", "Zabita denetim, tutanak ve mudahale kayitlari.",
    [("municipal_police_action_id", "bigint", "Zabita islem kimligi"),
     ("action_date", "date not null", "Islem tarihi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("action_type", "text", "Islem turu: Seyyar satici mudahalesi, Isgaliye denetimi, Pazar denetimi, Gurultu sikayeti, Insaat cevre duzeni, Etiket denetimi, Kaldirim isgali, Hafriyat denetimi, Dilencilik, Ilan ve reklam denetimi"),
     ("source", "text", "Kaynak: Rutin devriye, Vatandas ihbari, CIMER, Muhtar bildirimi, Kurum ici"),
     ("team_code", "text", "Zabita ekip kodu"),
     ("employee_id", "int", "Sorumlu zabita personeli"),
     ("result", "text", "Sonuc: Uyari, Tutanak duzenlendi, Idari para cezasi, Malzeme el konuldu, Faaliyetten men, Islem yapilmadi"),
     ("response_minutes", "int", "Ihbardan mudahaleye gecen sure (dakika)"),
     ("seized_item_count", "int", "El konulan urun/malzeme adedi")],
    pk="municipal_police_action_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("employee_id", "employee", "employee_id")],
    indexes=["action_date", "neighborhood_id", "action_type", "result"])

penalty_decision = T(
    "penalty_decision", "Idari para cezasi kararlari ve tahsilat durumu.",
    [("penalty_decision_id", "int", "Ceza karar kimligi"),
     ("municipal_police_action_id", "bigint", "Ilgili zabita islemi"),
     ("decision_date", "date not null", "Karar tarihi"),
     ("neighborhood_id", "int", "Mahalle"),
     ("business_id", "int", "Cezalandirilan isyeri (varsa)"),
     ("citizen_id", "int", "Cezalandirilan kisi (varsa)"),
     ("legal_basis", "text", "Dayanak: 1608 sayili Kanun, 5326 Kabahatler Kanunu, 3194 Imar Kanunu, 2872 Cevre Kanunu, 1593 Umumi Hifzissihha"),
     ("violation_type", "text", "Kabahat turu"),
     ("penalty_amount", MONEY, "Ceza tutari (TL)"),
     ("discounted_amount", MONEY, "Pesin odeme indirimli tutar (TL)"),
     ("collected_amount", MONEY, "Tahsil edilen (TL)"),
     ("payment_date", "date", "Tahsilat tarihi"),
     ("status", "text", "Durum: Tahsil edildi, Odenmedi, Itiraz edildi, Iptal edildi, Icraya verildi")],
    pk="penalty_decision_id",
    fks=[("municipal_police_action_id", "municipal_police_action", "municipal_police_action_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("business_id", "business", "business_id")],
    indexes=["decision_date", "status", "neighborhood_id"])

# ===========================================================================
# 9. FEN ISLERI / ALTYAPI / FILO
# ===========================================================================

road_work = T(
    "road_work", "Yol yapim, asfalt, kaldirim ve ustyapi calismalari.",
    [("road_work_id", "int", "Calisma kimligi"),
     ("street_id", "int", "Sokak"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("work_type", "text", "Calisma turu: Sicak asfalt, Yama, Parke tasi, Kaldirim yenileme, Bordur, Yagmur suyu izgara, Hemzemin duzenleme"),
     ("start_date", "date not null", "Baslangic"),
     ("end_date", "date", "Bitis"),
     ("area_m2", "numeric(12,2)", "Islem goren alan (m2)"),
     ("asphalt_ton", "numeric(12,2)", "Kullanilan asfalt (ton)"),
     ("cost_amount", MONEY, "Maliyet (TL)"),
     ("contract_id", "int", "Ilgili sozlesme"),
     ("executed_by", "text", "Yapan: Belediye ekibi, Yuklenici"),
     ("status", "text", "Durum: Tamamlandi, Devam ediyor, Planlandi, Iptal")],
    pk="road_work_id",
    fks=[("street_id", "street", "street_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("contract_id", "contract", "contract_id")],
    indexes=["start_date", "neighborhood_id", "work_type"])

park = T(
    "park", "Park, yesil alan ve cocuk oyun alanlari envanteri.",
    [("park_id", "int", "Park kimligi"),
     ("park_name", "text not null", "Park adi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("park_type", "text", "Tur: Mahalle parki, Cep parki, Semt bahcesi, Cocuk oyun alani, Spor alani, Koru"),
     ("area_m2", "numeric(12,2)", "Alan (m2)"),
     ("opening_year", "int", "Acilis yili"),
     ("playground_count", "int", "Oyun grubu adedi"),
     ("fitness_equipment_count", "int", "Fitness aleti adedi"),
     ("has_wc", "boolean", "Tuvalet var mi"),
     ("has_cafe", "boolean", "Kafeterya var mi"),
     ("irrigation_type", "text", "Sulama: Otomatik, Manuel, Damlama, Yok"),
     ("annual_maintenance_cost", MONEY, "Yillik bakim maliyeti (TL)"),
     ("tree_count", "int", "Agac sayisi"),
     ("accessibility_score", "int", "Engelli erisilebilirlik puani (0-100)")],
    pk="park_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["neighborhood_id", "park_type"])

street_light = T(
    "street_light", "Sokak aydinlatma direk envanteri ve enerji tuketimi.",
    [("street_light_id", "int", "Direk kimligi"),
     ("street_id", "int", "Sokak"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("lamp_type", "text", "Armatur tipi: LED, Sodyum buharli, Civa buharli, Metal halide"),
     ("power_watt", "int", "Guc (W)"),
     ("install_date", "date", "Montaj tarihi"),
     ("last_maintenance_date", "date", "Son bakim tarihi"),
     ("status", "text", "Durum: Calisiyor, Arizali, Bakimda, Sokuldu"),
     ("annual_kwh", "numeric(12,2)", "Yillik tahmini tuketim (kWh)")],
    pk="street_light_id",
    fks=[("street_id", "street", "street_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["neighborhood_id", "status", "lamp_type"])

infrastructure_fault = T(
    "infrastructure_fault", "Altyapi ariza ve mudahale kayitlari (aydinlatma, yol cokmesi, kanal, agac).",
    [("infrastructure_fault_id", "bigint", "Ariza kimligi"),
     ("report_date", "date not null", "Bildirim tarihi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("street_id", "int", "Sokak"),
     ("fault_type", "text", "Ariza turu: Sokak lambasi arizasi, Yol cokmesi, Rogar kapagi, Yagmur suyu tikanikligi, Devrilen agac, Kaldirim hasari, Trafik levhasi, Sinyalizasyon"),
     ("severity", "text", "Oncelik: Dusuk, Orta, Yuksek, Acil"),
     ("source", "text", "Kaynak: Vatandas, Zabita, Rutin kontrol, Muhtar, Diger kurum"),
     ("assigned_directorate_id", "int", "Sorumlu mudurluk"),
     ("resolution_date", "date", "Cozum tarihi"),
     ("resolution_hours", "numeric(8,2)", "Cozum suresi (saat)"),
     ("cost_amount", MONEY, "Mudahale maliyeti (TL)"),
     ("status", "text", "Durum: Cozuldu, Devam ediyor, Baska kuruma yonlendirildi, Iptal")],
    pk="infrastructure_fault_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("street_id", "street", "street_id"),
         ("assigned_directorate_id", "directorate", "directorate_id")],
    indexes=["report_date", "neighborhood_id", "fault_type", "status"])

vehicle = T(
    "vehicle", "Belediye arac ve is makinesi filosu.",
    [("vehicle_id", "int", "Arac kimligi"),
     ("plate_no", "text", "Plaka"),
     ("vehicle_class", "text", "Sinif: Cop kamyonu, Supurge araci, Arazoz, Kamyon, Kamyonet, Binek, Minibus, Is makinesi, Vinc, Cenaze araci, Ambulans"),
     ("brand", "text", "Marka"),
     ("model_year", "int", "Model yili"),
     ("fuel_type", "text", "Yakit: Motorin, Benzin, LPG, Elektrik, Hibrit"),
     ("directorate_id", "int", "Zimmetli mudurluk"),
     ("ownership", "text", "Mulkiyet: Belediye mali, Kiralik, Sirket araci"),
     ("acquisition_date", "date", "Edinim tarihi"),
     ("odometer_km", "int", "Guncel kilometre"),
     ("status", "text", "Durum: Aktif, Bakimda, Arizali, Hurdaya ayrildi"),
     ("monthly_rental_cost", MONEY, "Aylik kira bedeli (kiralik ise, TL)")],
    pk="vehicle_id",
    fks=[("directorate_id", "directorate", "directorate_id")],
    indexes=["vehicle_class", "directorate_id", "status"])

fuel_log = T(
    "fuel_log", "Arac akaryakit alim kayitlari.",
    [("fuel_log_id", "bigint", "Yakit kaydi kimligi"),
     ("vehicle_id", "int not null", "Arac"),
     ("fill_date", "date not null", "Alim tarihi"),
     ("liters", "numeric(10,2)", "Litre"),
     ("unit_price", "numeric(10,3)", "Litre fiyati (TL)"),
     ("amount", MONEY, "Tutar (TL)"),
     ("odometer_km", "int", "Kilometre"),
     ("station_name", "text", "Istasyon"),
     ("driver_employee_id", "int", "Soforu")],
    pk="fuel_log_id",
    fks=[("vehicle_id", "vehicle", "vehicle_id"),
         ("driver_employee_id", "employee", "employee_id")],
    indexes=["fill_date", "vehicle_id"])

vehicle_maintenance = T(
    "vehicle_maintenance", "Arac bakim ve onarim kayitlari.",
    [("vehicle_maintenance_id", "int", "Bakim kimligi"),
     ("vehicle_id", "int not null", "Arac"),
     ("service_date", "date not null", "Servis tarihi"),
     ("maintenance_type", "text", "Tur: Periyodik bakim, Ariza onarimi, Lastik, Kaza onarimi, Muayene, Kasko/sigorta"),
     ("odometer_km", "int", "Kilometre"),
     ("parts_cost", MONEY, "Parca maliyeti (TL)"),
     ("labor_cost", MONEY, "Iscilik maliyeti (TL)"),
     ("total_cost", MONEY, "Toplam maliyet (TL)"),
     ("downtime_days", "int", "Arac disi kalma suresi (gun)"),
     ("supplier_id", "int", "Servis saglayici")],
    pk="vehicle_maintenance_id",
    fks=[("vehicle_id", "vehicle", "vehicle_id"),
         ("supplier_id", "supplier", "supplier_id")],
    indexes=["service_date", "vehicle_id"])

municipal_facility = T(
    "municipal_facility", "Belediyeye ait bina ve tesisler (hizmet binasi, kultur merkezi, spor tesisi, pazar yeri).",
    [("municipal_facility_id", "int", "Tesis kimligi"),
     ("facility_name", "text not null", "Tesis adi"),
     ("facility_type", "text", "Tur: Hizmet binasi, Kultur merkezi, Spor tesisi, Kutuphane, Saglik merkezi, Pazar yeri, Sosyal tesis, Depo/santiye, Gencik merkezi, Kres, Asevi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("area_m2", "numeric(12,2)", "Kapali alan (m2)"),
     ("opening_year", "int", "Hizmete acilis yili"),
     ("capacity", "int", "Kapasite (kisi)"),
     ("staff_count", "int", "Calisan sayisi"),
     ("annual_operating_cost", MONEY, "Yillik isletme maliyeti (TL)"),
     ("annual_revenue", MONEY, "Yillik gelir (TL)"),
     ("is_accessible", "boolean", "Engelli erisimine uygun mu")],
    pk="municipal_facility_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["facility_type", "neighborhood_id"])

facility_energy_usage = T(
    "facility_energy_usage", "Tesis bazinda aylik elektrik, dogalgaz ve su tuketimi.",
    [("facility_energy_usage_id", "int", "Kayit kimligi"),
     ("municipal_facility_id", "int not null", "Tesis"),
     ("period_month", "date not null", "Ay"),
     ("electricity_kwh", "numeric(12,2)", "Elektrik tuketimi (kWh)"),
     ("electricity_cost", MONEY, "Elektrik bedeli (TL)"),
     ("gas_m3", "numeric(12,2)", "Dogalgaz tuketimi (m3)"),
     ("gas_cost", MONEY, "Dogalgaz bedeli (TL)"),
     ("water_m3", "numeric(12,2)", "Su tuketimi (m3)"),
     ("water_cost", MONEY, "Su bedeli (TL)"),
     ("solar_generation_kwh", "numeric(12,2)", "Cati GES uretimi (kWh)")],
    pk="facility_energy_usage_id",
    fks=[("municipal_facility_id", "municipal_facility", "municipal_facility_id")],
    indexes=["period_month", "municipal_facility_id"])

# ===========================================================================
# 10. TEMIZLIK VE CEVRE
# ===========================================================================

waste_collection = T(
    "waste_collection", "Gunluk mahalle bazli evsel atik toplama miktarlari ve maliyet.",
    [("waste_collection_id", "bigint", "Kayit kimligi"),
     ("collection_date", "date not null", "Toplama tarihi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("route_code", "text", "Guzergah kodu"),
     ("household_waste_ton", "numeric(10,3)", "Evsel atik (ton)"),
     ("bulky_waste_ton", "numeric(10,3)", "Iri hacimli atik (ton)"),
     ("market_waste_ton", "numeric(10,3)", "Pazar atigi (ton)"),
     ("total_ton", "numeric(10,3)", "Toplam atik (ton)"),
     ("trip_count", "int", "Sefer sayisi"),
     ("vehicle_id", "int", "Kullanilan arac"),
     ("crew_size", "int", "Ekip kisi sayisi"),
     ("transfer_station", "text", "Aktarma istasyonu"),
     ("disposal_cost", MONEY, "Bertaraf ve nakliye maliyeti (TL)")],
    pk="waste_collection_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("vehicle_id", "vehicle", "vehicle_id")],
    indexes=["collection_date", "neighborhood_id", "collection_date, neighborhood_id"])

recycling_stat = T(
    "recycling_stat", "Aylik geri donusum ve sifir atik verileri (mahalle bazinda).",
    [("recycling_stat_id", "int", "Kayit kimligi"),
     ("period_month", "date not null", "Ay"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("paper_ton", "numeric(10,3)", "Kagit-karton (ton)"),
     ("plastic_ton", "numeric(10,3)", "Plastik (ton)"),
     ("glass_ton", "numeric(10,3)", "Cam (ton)"),
     ("metal_ton", "numeric(10,3)", "Metal (ton)"),
     ("organic_ton", "numeric(10,3)", "Organik atik (ton)"),
     ("waste_oil_liter", "numeric(10,2)", "Atik bitkisel yag (litre)"),
     ("battery_kg", "numeric(10,2)", "Atik pil (kg)"),
     ("electronic_waste_kg", "numeric(10,2)", "Elektronik atik (kg)"),
     ("recycling_rate", "numeric(6,2)", "Geri kazanim orani (%)"),
     ("revenue_amount", MONEY, "Geri donusum geliri (TL)"),
     ("container_count", "int", "Geri donusum konteyneri sayisi")],
    pk="recycling_stat_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["period_month, neighborhood_id"])

air_quality_measurement = T(
    "air_quality_measurement", "Hava kalitesi olcum istasyonlarindan gunluk degerler.",
    [("air_quality_measurement_id", "bigint", "Olcum kimligi"),
     ("measurement_date", "date not null", "Olcum tarihi"),
     ("station_name", "text not null", "Istasyon adi"),
     ("neighborhood_id", "int", "Mahalle"),
     ("pm10", "numeric(8,2)", "PM10 (ug/m3)"),
     ("pm25", "numeric(8,2)", "PM2.5 (ug/m3)"),
     ("so2", "numeric(8,2)", "SO2 (ug/m3)"),
     ("no2", "numeric(8,2)", "NO2 (ug/m3)"),
     ("o3", "numeric(8,2)", "Ozon (ug/m3)"),
     ("co", "numeric(8,2)", "CO (mg/m3)"),
     ("aqi", "int", "Hava kalitesi indeksi"),
     ("aqi_category", "text", "Kategori: Iyi, Orta, Hassas, Saglıksiz, Kotu, Tehlikeli"),
     ("temperature_c", "numeric(6,2)", "Ortalama sicaklik (C)"),
     ("noise_db", "numeric(6,2)", "Ortalama gurultu seviyesi (dB)")],
    pk="air_quality_measurement_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["measurement_date", "station_name"])

# ===========================================================================
# 11. SOSYAL YARDIM VE DESTEK HIZMETLERI
# ===========================================================================

social_aid_application = T(
    "social_aid_application", "Sosyal yardim basvurulari ve sosyal inceleme sonuclari.",
    [("social_aid_application_id", "int", "Basvuru kimligi"),
     ("application_no", "text", "Basvuru numarasi"),
     ("application_date", "date not null", "Basvuru tarihi"),
     ("citizen_id", "int not null", "Basvuran vatandas"),
     ("household_id", "int", "Hane"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("aid_type", "text", "Yardim turu: Nakdi yardim, Gida yardimi, Yakacak yardimi, Kira yardimi, Egitim yardimi, Saglik/ilac yardimi, Engelli destegi, Asker ailesi yardimi, Giyim yardimi, Beyaz esya, Cenaze yardimi, Yeni dogan destegi"),
     ("household_income", MONEY, "Beyan edilen hane geliri (TL)"),
     ("household_size", "int", "Hane birey sayisi"),
     ("social_inquiry_date", "date", "Sosyal inceleme tarihi"),
     ("social_inquiry_score", "int", "Sosyal inceleme puani (0-100)"),
     ("status", "text", "Durum: Onaylandi, Reddedildi, Incelemede, Eksik evrak, Iptal edildi"),
     ("rejection_reason", "text", "Ret gerekcesi"),
     ("decision_date", "date", "Karar tarihi"),
     ("processing_days", "int", "Sonuclanma suresi (gun)"),
     ("approved_monthly_amount", MONEY, "Onaylanan aylik tutar (TL)"),
     ("support_duration_months", "int", "Destek suresi (ay)")],
    pk="social_aid_application_id",
    fks=[("citizen_id", "citizen", "citizen_id"),
         ("household_id", "household", "household_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["application_date", "neighborhood_id", "aid_type", "status"])

aid_payment = T(
    "aid_payment", "Onaylanan sosyal yardimlarin donemsel odemeleri / teslimleri.",
    [("aid_payment_id", "bigint", "Odeme kimligi"),
     ("social_aid_application_id", "int not null", "Basvuru"),
     ("citizen_id", "int", "Yararlanici"),
     ("neighborhood_id", "int", "Mahalle"),
     ("payment_date", "date not null", "Odeme/teslim tarihi"),
     ("aid_type", "text", "Yardim turu"),
     ("payment_form", "text", "Odeme sekli: Banka havalesi, Kent Kart yukleme, Ayni teslim, Vezne"),
     ("amount", MONEY, "Tutar veya ayni yardim degeri (TL)"),
     ("quantity", "int", "Adet (ayni yardimda)"),
     ("unit", "text", "Birim: Koli, Ton, Adet, Cift"),
     ("delivered_by", "text", "Teslim eden ekip")],
    pk="aid_payment_id",
    fks=[("social_aid_application_id", "social_aid_application", "social_aid_application_id"),
         ("citizen_id", "citizen", "citizen_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["payment_date", "citizen_id", "aid_type"])

soup_kitchen_daily = T(
    "soup_kitchen_daily", "Asevi gunluk sicak yemek uretim ve dagitim kayitlari.",
    [("soup_kitchen_daily_id", "int", "Kayit kimligi"),
     ("service_date", "date not null", "Tarih"),
     ("facility_name", "text", "Asevi adi"),
     ("meals_produced", "int", "Uretilen porsiyon"),
     ("meals_delivered_home", "int", "Eve teslim edilen porsiyon"),
     ("meals_served_onsite", "int", "Yerinde servis edilen porsiyon"),
     ("beneficiary_household_count", "int", "Hizmet verilen hane sayisi"),
     ("food_cost", MONEY, "Gida maliyeti (TL)"),
     ("cost_per_meal", MONEY, "Porsiyon basi maliyet (TL)"),
     ("is_ramadan", "boolean", "Ramazan donemi mi")],
    pk="soup_kitchen_daily_id",
    indexes=["service_date"])

# ===========================================================================
# 12. SAGLIK VE VETERINER HIZMETLERI
# ===========================================================================

health_center = T(
    "health_center", "Belediye saglik birimleri ve poliklinikleri.",
    [("health_center_id", "int", "Birim kimligi"),
     ("center_name", "text not null", "Birim adi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("service_types", "text", "Verilen hizmetler"),
     ("doctor_count", "int", "Hekim sayisi"),
     ("nurse_count", "int", "Hemsire/saglik personeli sayisi"),
     ("opening_year", "int", "Acilis yili"),
     ("daily_capacity", "int", "Gunluk hasta kapasitesi")],
    pk="health_center_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")])

clinic_visit = T(
    "clinic_visit", "Belediye poliklinik ve saglik hizmeti basvurulari.",
    [("clinic_visit_id", "bigint", "Muayene kimligi"),
     ("visit_date", "date not null", "Basvuru tarihi"),
     ("health_center_id", "int not null", "Saglik birimi"),
     ("citizen_id", "int", "Vatandas"),
     ("neighborhood_id", "int", "Mahalle"),
     ("service_type", "text", "Hizmet: Aile hekimligi destek, Dis poliklinigi, Fizik tedavi, Psikolojik danismanlik, Diyetisyen, Gebe izlem, Evde saglik, Tansiyon-seker olcum, Asi"),
     ("age_at_visit", "int", "Basvuru anindaki yas"),
     ("gender", "text", "Cinsiyet"),
     ("diagnosis_group", "text", "Tani grubu: Kas-iskelet, Dis-agiz, Solunum, Metabolik, Psikolojik, Kardiyovaskuler, Gebelik izlem, Koruyucu saglik, Diger"),
     ("is_first_visit", "boolean", "Ilk basvuru mu"),
     ("referral_made", "boolean", "Ust basamaga sevk edildi mi"),
     ("service_cost", MONEY, "Belediyeye maliyeti (TL)")],
    pk="clinic_visit_id",
    fks=[("health_center_id", "health_center", "health_center_id"),
         ("citizen_id", "citizen", "citizen_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["visit_date", "health_center_id", "service_type"])

veterinary_record = T(
    "veterinary_record", "Sokak hayvani rehabilitasyon, kisirlastirma, asilama ve sahiplendirme kayitlari.",
    [("veterinary_record_id", "int", "Kayit kimligi"),
     ("record_date", "date not null", "Islem tarihi"),
     ("neighborhood_id", "int", "Alindigi mahalle"),
     ("animal_type", "text", "Tur: Kopek, Kedi, Kus, Diger"),
     ("procedure_type", "text", "Islem: Kisirlastirma, Asilama, Tedavi, Mikrocip takma, Sahiplendirme, Barinaga alim, Dogal ortama birakma, Kuduz suphesi gozlem"),
     ("estimated_age_months", "int", "Tahmini yas (ay)"),
     ("gender", "text", "Cinsiyet: E, D"),
     ("microchip_no", "text", "Mikrocip numarasi"),
     ("shelter_days", "int", "Barinakta kalis suresi (gun)"),
     ("adopted", "boolean", "Sahiplendirildi mi"),
     ("cost_amount", MONEY, "Islem maliyeti (TL)"),
     ("veterinarian_name", "text", "Veteriner hekim")],
    pk="veterinary_record_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["record_date", "procedure_type", "neighborhood_id"])

# ===========================================================================
# 13. KULTUR, SPOR VE SOSYAL YASAM
# ===========================================================================

event = T(
    "event", "Belediye etkinlikleri: konser, tiyatro, sinema, festival, konferans, ramazan programi.",
    [("event_id", "int", "Etkinlik kimligi"),
     ("event_name", "text not null", "Etkinlik adi"),
     ("event_category", "text", "Kategori: Konser, Tiyatro, Sinema, Soylesi/konferans, Festival, Cocuk etkinligi, Sergi, Ramazan etkinligi, Spor turnuvasi, Anma toreni, Kermes"),
     ("event_date", "date not null", "Etkinlik tarihi"),
     ("municipal_facility_id", "int", "Mekan"),
     ("neighborhood_id", "int", "Mahalle"),
     ("venue_name", "text", "Mekan adi"),
     ("capacity", "int", "Kapasite"),
     ("attendance", "int", "Katilimci sayisi"),
     ("is_free", "boolean", "Ucretsiz mi"),
     ("ticket_price", MONEY, "Bilet fiyati (TL)"),
     ("cost_amount", MONEY, "Etkinlik maliyeti (TL)"),
     ("revenue_amount", MONEY, "Bilet geliri (TL)"),
     ("satisfaction_score", "numeric(4,2)", "Ortalama memnuniyet (1-5)"),
     ("target_audience", "text", "Hedef kitle: Genel, Cocuk, Genc, Kadin, Yasli, Engelli")],
    pk="event_id",
    fks=[("municipal_facility_id", "municipal_facility", "municipal_facility_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["event_date", "event_category", "neighborhood_id"])

event_attendance = T(
    "event_attendance", "Etkinlik katilim kayitlari (kayitli katilimcilar).",
    [("event_attendance_id", "bigint", "Katilim kimligi"),
     ("event_id", "int not null", "Etkinlik"),
     ("citizen_id", "int", "Vatandas"),
     ("registration_date", "date", "Kayit tarihi"),
     ("attended", "boolean", "Katildi mi"),
     ("channel", "text", "Kayit kanali: Mobil uygulama, Web, Telefon, Yerinde"),
     ("companion_count", "int", "Refakatci sayisi"),
     ("rating", "int", "Verilen puan (1-5)")],
    pk="event_attendance_id",
    fks=[("event_id", "event", "event_id"),
         ("citizen_id", "citizen", "citizen_id")],
    indexes=["event_id", "citizen_id"])

library = T(
    "library", "Belediye kutuphaneleri.",
    [("library_id", "int", "Kutuphane kimligi"),
     ("library_name", "text not null", "Kutuphane adi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("book_count", "int", "Kitap sayisi"),
     ("seat_count", "int", "Oturma kapasitesi"),
     ("member_count", "int", "Uye sayisi"),
     ("opening_year", "int", "Acilis yili"),
     ("has_study_hall", "boolean", "Etut salonu var mi"),
     ("is_24_hours", "boolean", "24 saat acik mi")],
    pk="library_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")])

book_loan = T(
    "book_loan", "Kutuphane odunc kitap islemleri.",
    [("book_loan_id", "bigint", "Odunc kimligi"),
     ("library_id", "int not null", "Kutuphane"),
     ("citizen_id", "int", "Uye"),
     ("book_title", "text", "Kitap adi"),
     ("book_category", "text", "Tur: Roman, Cocuk, Tarih, Bilim, Din, Siir, Kisisel gelisim, Ders kaynak, Sanat"),
     ("loan_date", "date not null", "Odunc alma tarihi"),
     ("due_date", "date", "Iade tarihi (planlanan)"),
     ("return_date", "date", "Gercek iade tarihi"),
     ("is_late", "boolean", "Gec iade mi"),
     ("late_days", "int", "Gecikme gun sayisi")],
    pk="book_loan_id",
    fks=[("library_id", "library", "library_id"),
         ("citizen_id", "citizen", "citizen_id")],
    indexes=["loan_date", "library_id", "citizen_id"])

sports_membership = T(
    "sports_membership", "Belediye spor tesisi uyelikleri ve kullanim bilgisi.",
    [("sports_membership_id", "int", "Uyelik kimligi"),
     ("municipal_facility_id", "int", "Spor tesisi"),
     ("citizen_id", "int", "Uye"),
     ("neighborhood_id", "int", "Mahalle"),
     ("branch", "text", "Brans: Yuzme, Fitness, Basketbol, Futbol, Voleybol, Tekvando, Judo, Masa tenisi, Pilates, Satranc, Jimnastik"),
     ("start_date", "date not null", "Uyelik baslangici"),
     ("end_date", "date", "Uyelik bitisi"),
     ("age_group", "text", "Yas grubu: Cocuk, Genc, Yetiskin, 65+"),
     ("gender", "text", "Cinsiyet"),
     ("fee_amount", MONEY, "Uyelik ucreti (TL)"),
     ("is_discounted", "boolean", "Indirimli/ucretsiz mi"),
     ("visit_count", "int", "Donem icindeki giris sayisi"),
     ("status", "text", "Durum: Aktif, Sona erdi, Dondurulmus, Iptal")],
    pk="sports_membership_id",
    fks=[("municipal_facility_id", "municipal_facility", "municipal_facility_id"),
         ("citizen_id", "citizen", "citizen_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["start_date", "branch", "municipal_facility_id"])

# ===========================================================================
# 14. VATANDAS ILISKILERI (Cozum Merkezi / Beyaz Masa)
# ===========================================================================

request_category = T(
    "request_category", "Vatandas basvuru kategorileri ve hedef cozum sureleri.",
    [("request_category_id", "int", "Kategori kimligi"),
     ("category_name", "text not null", "Ana kategori"),
     ("sub_category_name", "text", "Alt kategori"),
     ("responsible_directorate_id", "int", "Sorumlu mudurluk"),
     ("target_resolution_hours", "int", "Hedef cozum suresi (saat)"),
     ("priority", "text", "Oncelik: Dusuk, Normal, Yuksek, Acil")],
    pk="request_category_id",
    fks=[("responsible_directorate_id", "directorate", "directorate_id")])

service_request = T(
    "service_request", "Vatandas talep, sikayet, oneri ve ihbar kayitlari (Cozum Merkezi).",
    [("service_request_id", "bigint", "Basvuru kimligi"),
     ("request_no", "text", "Basvuru numarasi"),
     ("created_at", "timestamp not null", "Basvuru tarihi ve saati"),
     ("created_date", "date not null", "Basvuru tarihi"),
     ("request_category_id", "int", "Kategori"),
     ("request_type", "text", "Basvuru tipi: Sikayet, Talep, Oneri, Ihbar, Bilgi edinme, Tesekkur"),
     ("channel", "text", "Kanal: Cagri merkezi, Mobil uygulama, Web sitesi, CIMER, Sahsen basvuru, Sosyal medya, Muhtarlik, WhatsApp"),
     ("citizen_id", "int", "Basvuran vatandas"),
     ("neighborhood_id", "int", "Mahalle"),
     ("street_id", "int", "Sokak"),
     ("assigned_directorate_id", "int", "Atanan mudurluk"),
     ("assigned_employee_id", "int", "Atanan personel"),
     ("subject", "text", "Konu"),
     ("priority", "text", "Oncelik: Dusuk, Normal, Yuksek, Acil"),
     ("status", "text", "Durum: Cozuldu, Islemde, Yeni, Reddedildi, Baska kuruma yonlendirildi, Mukerrer"),
     ("first_response_hours", "numeric(8,2)", "Ilk donus suresi (saat)"),
     ("resolution_hours", "numeric(10,2)", "Toplam cozum suresi (saat)"),
     ("closed_at", "timestamp", "Kapanis tarihi"),
     ("sla_met", "boolean", "Hedef surede cozuldu mu"),
     ("reopened_count", "int", "Yeniden acilma sayisi"),
     ("satisfaction_score", "int", "Kapanis sonrasi memnuniyet puani (1-5)")],
    pk="service_request_id",
    fks=[("request_category_id", "request_category", "request_category_id"),
         ("citizen_id", "citizen", "citizen_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("assigned_directorate_id", "directorate", "directorate_id")],
    indexes=["created_date", "neighborhood_id", "status", "assigned_directorate_id",
             "request_category_id", "channel"])

service_request_log = T(
    "service_request_log", "Basvuru yasam dongusu hareketleri (atama, not, durum degisikligi).",
    [("service_request_log_id", "bigint", "Hareket kimligi"),
     ("service_request_id", "bigint not null", "Basvuru"),
     ("log_at", "timestamp not null", "Hareket zamani"),
     ("action", "text", "Islem: Kayit acildi, Mudurluge atandi, Personele atandi, Yerinde inceleme, Bilgi istendi, Cozuldu, Kapatildi, Yeniden acildi, Yonlendirildi"),
     ("from_status", "text", "Onceki durum"),
     ("to_status", "text", "Yeni durum"),
     ("directorate_id", "int", "Islemi yapan mudurluk"),
     ("note", "text", "Aciklama")],
    pk="service_request_log_id",
    fks=[("service_request_id", "service_request", "service_request_id")],
    indexes=["service_request_id", "log_at"])

survey = T(
    "survey", "Belediye anketleri (memnuniyet, ihtiyac analizi, hizmet degerlendirme).",
    [("survey_id", "int", "Anket kimligi"),
     ("survey_name", "text not null", "Anket adi"),
     ("survey_type", "text", "Tur: Genel memnuniyet, Hizmet degerlendirme, Ihtiyac analizi, Etkinlik degerlendirme, Butce katilim, Mahalle toplantisi, Personel memnuniyeti"),
     ("start_date", "date not null", "Baslangic tarihi"),
     ("end_date", "date", "Bitis tarihi"),
     ("method", "text", "Yontem: Yuz yuze, Telefon, Online, Mobil uygulama, Karma"),
     ("target_sample_size", "int", "Hedef ornek buyuklugu"),
     ("actual_sample_size", "int", "Gerceklesen katilimci sayisi"),
     ("margin_of_error", "numeric(5,2)", "Hata payi (%)"),
     ("conducted_by", "text", "Uygulayan: Belediye ekibi, Arastirma sirketi, Universite"),
     ("cost_amount", MONEY, "Anket maliyeti (TL)"),
     ("overall_satisfaction", "numeric(4,2)", "Genel memnuniyet ortalamasi (1-5)")],
    pk="survey_id",
    indexes=["start_date", "survey_type"])

survey_question = T(
    "survey_question", "Anket sorulari.",
    [("survey_question_id", "int", "Soru kimligi"),
     ("survey_id", "int not null", "Anket"),
     ("question_no", "int", "Soru sirasi"),
     ("question_text", "text not null", "Soru metni"),
     ("question_topic", "text", "Konu: Temizlik, Yollar ve altyapi, Park ve yesil alan, Zabita, Sosyal yardim, Kultur ve etkinlik, Ulasim, Imar, Cagri merkezi, Genel yonetim, Guvenlik, Gurultu"),
     ("question_type", "text", "Soru tipi: 5'li Likert, Evet-Hayir, Coktan secmeli, Acik uclu, Puanlama 0-10")],
    pk="survey_question_id",
    fks=[("survey_id", "survey", "survey_id")],
    indexes=["survey_id"])

survey_respondent = T(
    "survey_respondent", "Anket katilimcilari ve demografik profilleri.",
    [("survey_respondent_id", "int", "Katilimci kimligi"),
     ("survey_id", "int not null", "Anket"),
     ("citizen_id", "int", "Vatandas (eslesebiliyorsa)"),
     ("neighborhood_id", "int", "Mahalle"),
     ("response_date", "date", "Yanit tarihi"),
     ("age_band", "text", "Yas grubu"),
     ("gender", "text", "Cinsiyet"),
     ("education_level", "text", "Ogrenim durumu"),
     ("employment_status", "text", "Calisma durumu"),
     ("years_in_district", "int", "Ilcede ikamet suresi (yil)"),
     ("completed", "boolean", "Anketi tamamladi mi")],
    pk="survey_respondent_id",
    fks=[("survey_id", "survey", "survey_id"),
         ("citizen_id", "citizen", "citizen_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["survey_id", "neighborhood_id"])

survey_answer = T(
    "survey_answer", "Anket soru bazli yanitlar.",
    [("survey_answer_id", "bigint", "Yanit kimligi"),
     ("survey_id", "int not null", "Anket"),
     ("survey_question_id", "int not null", "Soru"),
     ("survey_respondent_id", "int not null", "Katilimci"),
     ("neighborhood_id", "int", "Mahalle (raporlama icin)"),
     ("answer_value", "int", "Sayisal yanit (Likert 1-5 veya puan 0-10)"),
     ("answer_label", "text", "Yanit etiketi: Cok memnunum, Memnunum, Kararsizim, Memnun degilim, Hic memnun degilim"),
     ("answer_text", "text", "Acik uclu yanit")],
    pk="survey_answer_id",
    fks=[("survey_id", "survey", "survey_id"),
         ("survey_question_id", "survey_question", "survey_question_id"),
         ("survey_respondent_id", "survey_respondent", "survey_respondent_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["survey_id", "survey_question_id", "neighborhood_id"])

# ===========================================================================
# 15. YONETISIM: MECLIS, ENCUMEN, SECIM
# ===========================================================================

council_meeting = T(
    "council_meeting", "Belediye meclisi toplantilari.",
    [("council_meeting_id", "int", "Toplanti kimligi"),
     ("meeting_date", "date not null", "Toplanti tarihi"),
     ("term_year", "int", "Yil"),
     ("session_type", "text", "Toplanti turu: Olagan, Olaganustu, Butce gorusmesi, Kesin hesap"),
     ("session_no", "int", "Birlesim numarasi"),
     ("member_count", "int", "Toplam uye sayisi"),
     ("attendee_count", "int", "Katilan uye sayisi"),
     ("agenda_item_count", "int", "Gundem maddesi sayisi"),
     ("decision_count", "int", "Alinan karar sayisi"),
     ("duration_minutes", "int", "Toplanti suresi (dakika)")],
    pk="council_meeting_id",
    indexes=["meeting_date"])

council_decision = T(
    "council_decision", "Belediye meclisi kararlari.",
    [("council_decision_id", "int", "Karar kimligi"),
     ("council_meeting_id", "int not null", "Toplanti"),
     ("decision_no", "text", "Karar numarasi"),
     ("decision_date", "date not null", "Karar tarihi"),
     ("topic", "text", "Konu basligi: Imar plani, Butce, Tarife, Kadro, Isim verme, Protokol, Borclanma, Tasinmaz, Komisyon raporu, Diger"),
     ("summary", "text", "Karar ozeti"),
     ("proposing_directorate_id", "int", "Teklif eden mudurluk"),
     ("vote_result", "text", "Oylama sonucu: Oybirligi, Oycoklugu, Reddedildi, Komisyona havale"),
     ("yes_votes", "int", "Kabul oyu"),
     ("no_votes", "int", "Ret oyu"),
     ("abstain_votes", "int", "Cekimser"),
     ("neighborhood_id", "int", "Ilgili mahalle (varsa)"),
     ("financial_impact", MONEY, "Mali etki (TL)")],
    pk="council_decision_id",
    fks=[("council_meeting_id", "council_meeting", "council_meeting_id"),
         ("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["decision_date", "topic", "vote_result"])

committee_decision = T(
    "committee_decision", "Belediye encumeni kararlari.",
    [("committee_decision_id", "int", "Encumen karar kimligi"),
     ("decision_date", "date not null", "Karar tarihi"),
     ("decision_no", "text", "Karar numarasi"),
     ("topic", "text", "Konu: Imar cezasi, Isyeri kapatma, Ihale onayi, Kamulastirma, Tahsis, Yikim karari, Para cezasi, Harcama izni"),
     ("related_directorate_id", "int", "Ilgili mudurluk"),
     ("neighborhood_id", "int", "Mahalle"),
     ("result", "text", "Sonuc: Kabul, Ret, Ertelendi"),
     ("financial_impact", MONEY, "Mali etki (TL)")],
    pk="committee_decision_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["decision_date", "topic"])

election_result = T(
    "election_result", "Mahalle bazli yerel secim sonuclari (kurgusal parti isimleri).",
    [("election_result_id", "int", "Kayit kimligi"),
     ("election_year", "int not null", "Secim yili"),
     ("election_type", "text", "Secim turu: Yerel secim, Genel secim, Referandum"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("party_code", "text", "Parti/secenek kodu (kurgusal: A Partisi, B Partisi, ...)"),
     ("vote_count", "int", "Alinan oy"),
     ("vote_share", "numeric(6,2)", "Oy orani (%)"),
     ("registered_voters", "int", "Kayitli secmen sayisi"),
     ("turnout_rate", "numeric(6,2)", "Katilim orani (%)"),
     ("invalid_votes", "int", "Gecersiz oy")],
    pk="election_result_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["election_year, neighborhood_id"])

# ===========================================================================
# 16. DIGER HIZMETLER: MEZARLIK, OTOPARK, ACIL DURUM
# ===========================================================================

burial_record = T(
    "burial_record", "Defin ve cenaze hizmetleri kayitlari.",
    [("burial_record_id", "int", "Defin kimligi"),
     ("burial_date", "date not null", "Defin tarihi"),
     ("cemetery_name", "text", "Mezarlik adi"),
     ("neighborhood_id", "int", "Merhumun ikamet mahallesi"),
     ("death_record_id", "int", "Ilgili olum kaydi"),
     ("age_at_death", "int", "Vefat yasi"),
     ("gender", "text", "Cinsiyet"),
     ("service_type", "text", "Hizmet: Tam cenaze hizmeti, Sadece nakil, Sadece defin, Gassal hizmeti"),
     ("transport_distance_km", "numeric(8,2)", "Nakil mesafesi (km)"),
     ("fee_amount", MONEY, "Alinan ucret (TL, cogu ucretsiz)"),
     ("cost_amount", MONEY, "Belediyeye maliyeti (TL)"),
     ("is_free_service", "boolean", "Ucretsiz hizmet mi")],
    pk="burial_record_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id"),
         ("death_record_id", "death_record", "death_record_id")],
    indexes=["burial_date", "cemetery_name"])

parking_lot = T(
    "parking_lot", "Belediye otoparklari (Ilce Otopark A.S. isletmesi).",
    [("parking_lot_id", "int", "Otopark kimligi"),
     ("lot_name", "text not null", "Otopark adi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("lot_type", "text", "Tur: Yol ustu, Kapali otopark, Acik alan, Katli otopark"),
     ("capacity", "int", "Arac kapasitesi"),
     ("hourly_rate", MONEY, "Saatlik ucret (TL)"),
     ("monthly_rate", MONEY, "Aylik abonelik (TL)"),
     ("opening_year", "int", "Isletmeye acilis yili"),
     ("is_ev_charging", "boolean", "Elektrikli arac sarj noktasi var mi")],
    pk="parking_lot_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")])

parking_transaction = T(
    "parking_transaction", "Otopark giris-cikis ve ucret tahsilat kayitlari.",
    [("parking_transaction_id", "bigint", "Islem kimligi"),
     ("parking_lot_id", "int not null", "Otopark"),
     ("entry_at", "timestamp not null", "Giris zamani"),
     ("entry_date", "date not null", "Giris tarihi"),
     ("exit_at", "timestamp", "Cikis zamani"),
     ("duration_minutes", "int", "Kalis suresi (dakika)"),
     ("vehicle_class", "text", "Arac sinifi: Otomobil, Minibus, Motosiklet, Ticari"),
     ("payment_method", "text", "Odeme: Nakit, Kredi kartı, Kent Kart, Mobil uygulama, Abonelik"),
     ("amount", MONEY, "Tahsil edilen tutar (TL)"),
     ("is_subscriber", "boolean", "Abone mi")],
    pk="parking_transaction_id",
    fks=[("parking_lot_id", "parking_lot", "parking_lot_id")],
    indexes=["entry_date", "parking_lot_id"])

emergency_call = T(
    "emergency_call", "Afet ve acil durum mudahale kayitlari (yangin destegi, su baskini, kar, deprem tatbikati).",
    [("emergency_call_id", "int", "Kayit kimligi"),
     ("call_at", "timestamp not null", "Cagri zamani"),
     ("call_date", "date not null", "Cagri tarihi"),
     ("neighborhood_id", "int not null", "Mahalle"),
     ("event_type", "text", "Olay turu: Su baskini, Yangin destegi, Kar mucadelesi, Firtina hasari, Agac devrilmesi, Deprem ihbari, Coken yol, Asansorde mahsur, Sel"),
     ("severity", "text", "Siddet: Dusuk, Orta, Yuksek, Kritik"),
     ("response_minutes", "int", "Olay yerine varis suresi (dakika)"),
     ("crew_count", "int", "Gorevlendirilen ekip sayisi"),
     ("vehicle_count", "int", "Gorevlendirilen arac sayisi"),
     ("affected_building_count", "int", "Etkilenen bina sayisi"),
     ("affected_person_count", "int", "Etkilenen kisi sayisi"),
     ("damage_estimate", MONEY, "Tahmini hasar (TL)"),
     ("response_cost", MONEY, "Mudahale maliyeti (TL)"),
     ("status", "text", "Durum: Tamamlandi, Devam ediyor, Diger kuruma devredildi")],
    pk="emergency_call_id",
    fks=[("neighborhood_id", "neighborhood", "neighborhood_id")],
    indexes=["call_date", "neighborhood_id", "event_type"])

# ---------------------------------------------------------------------------
# Ileri referans iceren FK'lar (tanim sirasi yuzunden burada eklenir)
# ---------------------------------------------------------------------------
budget_line.fks.append(("directorate_id", "directorate", "directorate_id"))
revenue_transaction.fks.append(("directorate_id", "directorate", "directorate_id"))
expense_transaction.fks += [("directorate_id", "directorate", "directorate_id"),
                            ("supplier_id", "supplier", "supplier_id"),
                            ("contract_id", "contract", "contract_id")]
tender.fks.append(("directorate_id", "directorate", "directorate_id"))
contract.fks.append(("directorate_id", "directorate", "directorate_id"))
payment_order.fks.append(("directorate_id", "directorate", "directorate_id"))
business_inspection.fks.append(("inspector_employee_id", "employee", "employee_id"))
service_request.fks += [("assigned_employee_id", "employee", "employee_id"),
                        ("street_id", "street", "street_id")]
service_request_log.fks.append(("directorate_id", "directorate", "directorate_id"))
council_decision.fks.append(("proposing_directorate_id", "directorate", "directorate_id"))
committee_decision.fks.append(("related_directorate_id", "directorate", "directorate_id"))
penalty_decision.fks.append(("citizen_id", "citizen", "citizen_id"))
event.fks.append(("neighborhood_id", "neighborhood", "neighborhood_id")) if False else None
