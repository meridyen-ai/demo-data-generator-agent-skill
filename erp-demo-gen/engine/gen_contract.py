"""Talaşlı imalat / fason metal parça üreticisi jeneratörü (contract_machining).

Gaziantep 2. OSB'de 30.000 m² tesisi olan, OEM ve Tier-1 müşterilere yüksek
adetli hassas talaşlı parça üreten, yakın pazarlara ihracat yapan bir firmayı
modeller. Genel `manufacturing` yolundan ayrıldığı yerler:

* **Çok para birimli, TRY tabanlı.** Türk lirası taban para birimi; ihracat
  EUR/USD ile faturalanır. Türkiye enflasyonu nedeniyle nominal TL fiyatları
  yıllar içinde 3 kattan fazla artar; bu yüzden ürün fiyat ve maliyetleri EUR
  referansında tutulup işlem tarihindeki kurla TL'ye çevrilir. Böylece hem TL
  cirosu gerçekçi biçimde şişer hem de EUR/USD bazında analiz tutarlı kalır.
  Her belge TRY + EUR + USD tutarını birlikte taşır.
* **Operasyon bazlı üretim.** Her parçanın bir rotası (routings) vardır; iş
  emirleri operasyon operasyon işlenir (production_operations): kurulum ve
  işleme süresi, tezgah, operatör, vardiya, duruş, hurda, fire.
* **Fason operasyonlar.** Isıl işlem, kaplama, taşlama dışarıda yaptırılır ve
  ayrı bir tedarik zinciri kurar (subcontract_operations).
* **Kalite.** Girdi/proses/final kontrol ölçümleri, uygunsuzluk (NCR/8D),
  müşteri şikayeti ve PPM takibi.
* **Maliyet ayrımı.** SMM (620) yalnızca *direkt* maliyettir: hammadde, direkt
  işçilik, fason, kesici takım. Üretim genel giderleri (enerji, üretim
  amortismanı, endirekt üretim personeli, bakım, kalite, fabrika genel) ile
  pazarlama/genel yönetim/Ar-Ge/finansman/vergi `expenses` tablosunda tutulur.
  Hiçbir maliyet iki kez sayılmaz; tam yükleme (full absorption) brüt kâr da
  v_pnl_* görünümlerinde ayrıca hesaplanır.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from . import locales
from .gen_backoffice import BackOfficeMixin
from .generators import Gen, WeightedPicker
from .util import money, add_days, add_months, random_date_in_month, days_in_month

# ---------------------------------------------------------------- sözlükler --
CURRENCY_NAMES = {
    "TRY": ("Türk Lirası", "₺"), "EUR": ("Euro", "€"), "USD": ("ABD Doları", "$"),
    "GBP": ("İngiliz Sterlini", "£"),
}

# durum değerleri (tek yerde tanımlı ki görünümler ve kontroller ile tutarlı kalsın)
SO_DONE, SO_OPEN, SO_CANCEL = "Tamamlandı", "Açık", "İptal"
INV_PAID, INV_OPEN, INV_LATE = "Ödendi", "Açık", "Vadesi Geçti"
PO_RECEIVED, PO_OPEN, PO_CANCEL = "Teslim Alındı", "Açık", "İptal"
WO_DONE, WO_WIP, WO_PLANNED, WO_CANCEL = "Tamamlandı", "Devam Ediyor", "Planlandı", "İptal"
MOVE_IN, MOVE_OUT = "Giriş", "Çıkış"

PAYMENT_METHODS = ["Havale / EFT", "Vadeli Çek", "DBS (Doğrudan Borçlandırma)",
                   "Akreditif (L/C)", "Peşin Havale", "Senet", "Nakit"]
VENDOR_PAY_METHODS = ["Havale / EFT", "Vadeli Çek", "Akreditif (L/C)", "Senet", "Peşin Havale"]

DOWNTIME_REASONS = [
    "Takım değişimi", "Kalıp / aparat ayarı", "Tezgah arızası", "Elektrik kesintisi",
    "Malzeme bekleme", "Ölçü kontrol bekleme", "Planlı bakım", "Talaş boşaltma",
    "Soğutma sıvısı takviyesi", "Program düzeltme", "Operatör molası",
    "Kalite onayı bekleme", "Fason dönüş bekleme", "Vardiya devir teslimi",
]

DEFECT_CODES = [
    ("D01", "Çap ölçüsü tolerans dışı", "Tezgah ayarı / takım aşınması"),
    ("D02", "Yüzey pürüzlülüğü yüksek", "Kesici takım aşınması"),
    ("D03", "Diş açma hatası", "Kılavuz aşınması"),
    ("D04", "Çapak temizlenmemiş", "Çapak alma operasyonu atlanmış"),
    ("D05", "Konsantriklik / salgı hatası", "Bağlama aparatı toleransı"),
    ("D06", "Delik pozisyon hatası", "Fikstür konumlandırma"),
    ("D07", "Malzeme çatlağı", "Hammadde kalitesi"),
    ("D08", "Sertlik değeri düşük", "Isıl işlem parametresi"),
    ("D09", "Kaplama kalınlığı yetersiz", "Fason kaplama prosesi"),
    ("D10", "Korozyon / pas", "Yağlama ve ambalajlama"),
    ("D11", "Yanlış malzeme kalitesi", "Depo karışıklığı"),
    ("D12", "Ezik / darbe izi", "Taşıma ve ambalajlama"),
    ("D13", "Eksik operasyon", "İş emri takibi"),
    ("D14", "Etiket / izlenebilirlik hatası", "Etiketleme prosedürü"),
    ("D15", "Ölçü raporu uygunsuz", "Ölçüm ekipmanı kalibrasyonu"),
    ("D16", "Kaynak / montaj hatası", "Montaj talimatı"),
]

ROOT_CAUSE_CATEGORIES = ["Makine", "Malzeme", "Metot", "İnsan", "Ölçüm", "Çevre", "Tedarikçi"]
DISPOSITIONS = ["Hurda", "Yeniden İşleme (Rework)", "Şartlı Kabul", "Tedarikçiye İade",
                "Sapma Onayı (Sapma Talebi)", "Sınıflandırma (Sorting)"]

INSPECTION_TYPES = ["Girdi Kontrol", "İlk Parça Onayı (İPO)", "Proses Ara Kontrol",
                    "Final Kontrol", "Sevkiyat Öncesi Kontrol", "Periyodik SPC Ölçümü"]
MEASUREMENT_METHODS = ["Dijital Kumpas", "Mikrometre", "CMM (Koordinat Ölçüm)",
                       "Komparatör Saat", "Pasametre", "Yüzey Pürüzlülük Cihazı",
                       "Sertlik Ölçüm (HRC)", "Profil Projektör", "Mastar / Kalibre",
                       "Optik Ölçüm Cihazı"]
QUALITY_CHARACTERISTICS = [
    ("Dış çap", "mm"), ("İç çap", "mm"), ("Toplam boy", "mm"), ("Delik pozisyonu", "mm"),
    ("Diş adımı", "mm"), ("Yüzey pürüzlülüğü Ra", "µm"), ("Salgı (konsantriklik)", "mm"),
    ("Sertlik", "HRC"), ("Kaplama kalınlığı", "µm"), ("Dikliğe göre açı", "°"),
    ("Cep derinliği", "mm"), ("Pah ölçüsü", "mm"),
]

MAINTENANCE_TYPES = ["Planlı Periyodik Bakım", "Arıza Bakım", "Kestirimci Bakım",
                     "Kalibrasyon", "Revizyon / Overhol", "Yağ ve Filtre Değişimi"]
FAILURE_MODES = ["Fener mili arızası", "Servo motor arızası", "Hidrolik kaçak",
                 "Kızak / kayar yüzey aşınması", "Bilyalı vida boşluğu",
                 "Takım değiştirici arızası", "Soğutma sistemi tıkanması",
                 "Elektrik panosu arızası", "Enkoder hatası", "Konveyör arızası",
                 "Çubuk sürücü (bar feeder) arızası", "Yazılım / kontrol hatası"]

HSE_TYPES = ["Ramak Kala", "Küçük Yaralanma", "İlk Yardım Vakası", "Kayıp Günlü İş Kazası",
             "Malzeme Hasarı", "Yangın / Duman", "Kimyasal Temas", "Ergonomik Şikayet"]
HSE_BODY_PARTS = ["El / Parmak", "Göz", "Ayak", "Kol", "Sırt / Bel", "Baş", "Yok"]

LEAD_SOURCES_TR = [
    "Web sitesi formu", "LinkedIn görüşmesi", "Fuar (WIN EURASIA)", "Fuar (Automechanika)",
    "Fuar (Hannover Messe)", "Fuar (EMO)", "Referans / Mevcut müşteri",
    "İhracatçı birlikleri yönlendirmesi", "Ticaret müşavirliği", "Soğuk arama",
    "E-posta kampanyası", "OSB iş birliği", "Tedarikçi portalı kaydı",
    "Sektör dergisi ilanı", "Mevcut müşteriden yeni proje",
]
WIN_REASONS_TR = ["Fiyat avantajı", "Kısa termin", "Kalite ve PPM performansı",
                  "Kapasite esnekliği", "Mevcut iş ilişkisi", "IATF 16949 belgesi",
                  "Numune onayının hızlı alınması", "Yerlileştirme projesi",
                  "Tek kaynaktan tüm operasyonlar"]
LOSS_REASONS_TR = ["Fiyat yüksek kaldı", "Rakip daha kısa termin verdi",
                   "Müşteri projeyi erteledi", "Kapasite yetersizliği",
                   "Numune onayı alınamadı", "Uzak Doğu tedarikçisi tercih edildi",
                   "Müşteri iç üretime aldı", "Ödeme vadesinde anlaşılamadı",
                   "Yatırım gerektirdiği için çekildik"]
COMPETITORS_TR = ["Bursa merkezli rakip", "Konya merkezli rakip", "Ankara merkezli rakip",
                  "İzmir merkezli rakip", "Çek Cumhuriyeti tedarikçisi",
                  "Polonya tedarikçisi", "Hindistan tedarikçisi", "Çin tedarikçisi",
                  "Müşterinin iç üretimi", "Portekiz tedarikçisi"]
ACTIVITY_TYPES_TR = ["Telefon görüşmesi", "E-posta yazışması", "Müşteri ziyareti",
                     "Teklif gönderimi", "Teknik toplantı", "Numune sunumu",
                     "Fabrika denetimi (audit)", "Fiyat revizyon görüşmesi",
                     "Fuar görüşmesi", "Termin takibi", "Video konferans"]

CUSTOMS_OFFICES = [
    "Gaziantep Gümrük Müdürlüğü", "Gaziantep Havalimanı Gümrük Müdürlüğü",
    "İskenderun Liman Gümrük Müdürlüğü", "Mersin Liman Gümrük Müdürlüğü",
    "Kapıkule Gümrük Müdürlüğü", "Habur Gümrük Müdürlüğü",
    "Cilvegözü Gümrük Müdürlüğü", "Öncüpınar Gümrük Müdürlüğü",
    "Sarp Gümrük Müdürlüğü", "Gürbulak Gümrük Müdürlüğü",
]
BORDER_GATES = ["Kapıkule", "Hamzabeyli", "İpsala", "Habur", "Gürbulak", "Sarp",
                "Cilvegözü", "Öncüpınar", "Mersin Limanı", "İskenderun Limanı",
                "Gaziantep Havalimanı"]

BANK_NAMES = ["Ziraat Bankası", "İş Bankası", "Garanti BBVA", "Akbank", "Yapı Kredi",
              "Halkbank", "VakıfBank", "QNB", "TEB", "Denizbank"]


class ContractMachiningGen(BackOfficeMixin, Gen):

    # =============================================================== kurulum ==
    def __init__(self, profile, seeds, tuning, rng):
        super().__init__(profile, seeds, tuning, rng)
        self.base_ccy = tuning.get("base_currency", "TRY")
        self.start_date = date(profile.start_year, 1, 1)
        self.end_month = int(getattr(profile, "end_month", 12) or 12)
        self.vat_rate = float(tuning.get("vat_rate", 0.20))
        self.home_cc = tuning.get("home_country_code", "TR")
        self.home_country = tuning.get("home_country", "Türkiye")
        self.export_share = float(tuning.get("export_revenue_share", 0.36))
        self.real_cost_drift = float(tuning.get("real_cost_drift", 0.028))
        self.real_price_drift = float(tuning.get("real_price_drift", 0.012))
        self._call_off_div = float(tuning.get("call_off_divisor", 6.0))
        self._fx_cache = {}
        self._entry_no = 0
        self._n_days = (self._today() - self.start_date).days + 1

    def _today(self):
        y = self.p.end_year()
        m = self.end_month
        return date(y, m, days_in_month(y, m))

    def months(self):
        for yi in range(self.p.years):
            year = self.p.start_year + yi
            last = self.end_month if yi == self.p.years - 1 else 12
            for m in range(1, last + 1):
                yield yi, year, m

    def _clamp(self, d):
        t = self._today()
        return d if d <= t else t

    # ==================================================================== kur ==
    def gen_currencies(self):
        used = [self.base_ccy] + [c for c in self.t.get("trade_currencies", [])
                                  if c != self.base_ccy]
        for code in used:
            name, sym = CURRENCY_NAMES.get(code, (code, code))
            self.add("currencies", {
                "code": code, "name": name, "symbol": sym,
                "is_base": code == self.base_ccy, "decimals": 2,
            })

    def gen_fx_rates(self):
        """Yıllık çapa değerlerinden türetilen, ortalamaya dönen rastgele
        yürüyüşle günlük TCMB benzeri kur serisi. Çapalar TL/birim olarak
        okunur, tabloya taban para birimi başına oran olarak yazılır."""
        r = self.rng.stream("fx")
        anchors_cfg = self.t.get("fx_anchors_try_per_unit", {})
        n = self._n_days
        for cur in [c["code"] for c in self.rows("currencies")]:
            if cur == self.base_ccy:
                self._fx_cache[cur] = [1.0] * n
                series_try = [1.0] * n
            else:
                anchors = {int(k): float(v) for k, v in anchors_cfg.get(cur, {}).items()}
                if not anchors:
                    continue
                yrs = sorted(anchors)

                def anc(y, _a=anchors, _y=yrs):
                    return _a.get(y) or _a[min(max(y, _y[0]), _y[-1])]

                drift = 0.0
                series_try = []
                for i in range(n):
                    d = add_days(self.start_date, i)
                    # Çapa değerleri YILLIK ORTALAMA kurdur; bu yüzden yıl ortasına
                    # (1 Temmuz) oturtulur ve iki yıl ortası arasında doğrusal
                    # yürütülür. Yıl başına oturtulursa yılın ortalaması bir
                    # sonraki yılın kuruna kayar ve EUR bazlı ciro sistematik
                    # olarak düşük çıkar.
                    frac = (d.timetuple().tm_yday - 1) / 366.0
                    a_cur = anc(d.year)
                    if frac < 0.5:
                        a_ref = anc(d.year - 1)
                        smooth = a_ref + (a_cur - a_ref) * (frac + 0.5)
                    else:
                        a_ref = anc(d.year + 1)
                        smooth = a_cur + (a_ref - a_cur) * (frac - 0.5)
                    # TL'de oynaklık tek yönlüdür: sıçramalar yukarı, geri
                    # çekilmeler yavaştır. Rastgele yürüyüşü buna göre eğiyoruz.
                    shock = 0.012 if r.chance(0.006) else 0.0
                    drift = drift * 0.988 + (r.rand() * 0.0042 - 0.0019) + shock
                    drift = max(-0.035, min(0.055, drift))
                    series_try.append(smooth * (1 + drift))
                self._fx_cache[cur] = [1.0 / v if v else 1.0 for v in series_try]
            step = 1
            for i in range(0, n, step):
                try_per_unit = series_try[i]
                per_base = self._fx_cache[cur][i]
                self.add("fx_rates", {
                    "id": self.nid("fx_rates"), "rate_date": add_days(self.start_date, i),
                    "currency_code": cur, "base_currency": self.base_ccy,
                    "rate_per_base": round(per_base, 8),
                    "base_per_unit": round(try_per_unit, 8),
                })

    def fx(self, currency, d) -> float:
        """1 TL karşılığı `currency` tutarı (ör. EUR için 0,0187)."""
        if currency == self.base_ccy:
            return 1.0
        s = self._fx_cache.get(currency)
        if not s:
            return 1.0
        i = max(0, min((d - self.start_date).days, len(s) - 1))
        return s[i]

    def try_per(self, currency, d) -> float:
        """1 birim `currency` karşılığı TL (ör. EUR için 53,40)."""
        rate = self.fx(currency, d)
        return 1.0 / rate if rate else 1.0

    def to_base(self, amount, currency, d) -> float:
        return money(amount * self.try_per(currency, d))

    @staticmethod
    def _fxr(rate: float) -> float:
        """Belgeye YAZILAN kur. Hesaplamalarda 1 TL karşılığı döviz (0,0187)
        kullanılır; belgede ise Türkiye'de okunduğu haliyle 1 birim döviz
        karşılığı TL (53,40) saklanır. Bu hem doğal hem de hassastır: 0,0187
        dört ondalıkla saklandığında EUR karşılıkları binde bir sapardı."""
        return round(1.0 / rate, 6) if rate else 1.0

    def eur(self, amount_try, d) -> float:
        return money(amount_try * self.fx("EUR", d))

    def usd(self, amount_try, d) -> float:
        return money(amount_try * self.fx("USD", d))

    def _mc(self, amount_try, d, prefix=""):
        """TL tutarını EUR/USD karşılıklarıyla birlikte döndürür."""
        return {f"{prefix}eur": self.eur(amount_try, d), f"{prefix}usd": self.usd(amount_try, d)}

    def _drift(self, d, rate):
        """Kur artışının üzerine binen reel artış katsayısı (referans: son yıl)."""
        years = (d - date(self.p.end_year(), 6, 30)).days / 365.25
        return (1 + rate) ** years

    # ============================================================= referanslar ==
    def gen_company(self):
        c = self.s["company"]
        self.add("company", {
            "id": 1, "name": c["name"], "legal_name": c.get("legal_name", c["name"]),
            "tagline": c.get("tagline", ""),
            "founded_year": c.get("founded_year", self.p.start_year - 12),
            "hq_address": c.get("hq_address", ""), "hq_city": c.get("hq_city", "Gaziantep"),
            "hq_postcode": c.get("hq_postcode", ""),
            "hq_country": c.get("hq_country", self.home_country),
            "vat_number": c.get("vat_number", ""),
            "registration_no": c.get("registration_no", ""),
            "domain": c["domain"], "base_currency": self.base_ccy,
            "fiscal_year_end": "31-12", "employee_count": self.p.employees,
            "website": f"https://www.{c['domain']}", "phone": c.get("phone", ""),
            "plant_area_sqm": c.get("plant_area_sqm", 30000),
            "closed_area_sqm": c.get("closed_area_sqm", 22000),
            "osb_name": c.get("osb_name", ""),
            "iso_certificates": c.get("iso_certificates", ""),
            "shift_model": c.get("shift_model", "3 vardiya / 7 gün"),
            "export_country_count": c.get("export_country_count", 0),
        })

    def gen_tax_codes(self):
        for i, tc in enumerate(self.t.get("tax_codes", []), start=1):
            self.add("tax_codes", {
                "id": i, "code": tc["code"], "name": tc["name"], "rate_pct": tc["rate_pct"],
                "tax_type": tc.get("tax_type", "KDV"), "region": tc.get("region", "TR"),
                "applies_to": tc.get("applies_to", "sales"),
                "description": tc.get("description", ""),
            })

    def gen_chart_of_accounts(self):
        for a in self.s.get("chart_of_accounts", []):
            self.add("chart_of_accounts", {
                "id": self.nid("chart_of_accounts"), "account_code": a["code"],
                "account_name": a["name"], "account_type": a["type"],
                "account_subtype": a.get("subtype", ""), "normal_side": a.get("side", "debit"),
                "is_pnl": a.get("is_pnl", False), "pnl_section": a.get("pnl_section", ""),
                "parent_code": a.get("parent", None),
            })
        self._acct = {a["account_code"]: a["account_name"] for a in self.rows("chart_of_accounts")}

    def gen_expense_categories(self):
        for c in self.s.get("expense_categories", []):
            self.add("expense_categories", {
                "id": self.nid("expense_categories"), "code": c["code"], "name": c["name"],
                "expense_group": c.get("group", "Genel Yönetim Giderleri"),
                "account_code": c["account_code"],
                "is_fixed": c.get("variability_pct", 0) < 25,
                "variability_pct": c.get("variability_pct", 0),
                "is_cash": c.get("is_cash", True), "description": c.get("description", ""),
            })
        self._exp_cat = {c["code"]: c for c in self.s.get("expense_categories", [])}
        self._cat_row = {c["code"]: c for c in self.rows("expense_categories")}

    def gen_departments(self):
        for d in self.s["departments"]:
            if isinstance(d, str):
                d = {"name": d}
            did = self.nid("departments")
            self.add("departments", {
                "id": did, "name": d["name"],
                "cost_center": d.get("cost_center", f"MM-{1000 + did}"),
                "manager_id": None, "is_production": bool(d.get("is_production", False)),
                "headcount_target": sum(int(x.get("count", 1)) for x in d.get("roles", [])),
                "description": d.get("description", ""),
            })
            self.rows("departments")[-1]["_payroll_category"] = d.get("payroll_category")
        self._dept_seed = {d["name"]: d for d in self.s["departments"] if isinstance(d, dict)}
        self._dept_by_name = {d["name"]: d["id"] for d in self.rows("departments")}
        self._dept_row = {d["id"]: d for d in self.rows("departments")}
        self._production_depts = {d["id"] for d in self.rows("departments") if d["is_production"]}

    def gen_warehouses(self):
        r = self.rng.stream("wh")
        for w in self.s["warehouses"]:
            wid = self.nid("warehouses")
            self.add("warehouses", {
                "id": wid, "code": w["code"], "name": w["name"],
                "type": w.get("type", "Ambar"), "city": w.get("city", "Gaziantep"),
                "state": w.get("state", "Gaziantep"), "country": w.get("country", self.home_country),
                "capacity_sqft": int(float(w.get("capacity_sqm", 2000)) * 10.7639),
                "country_code": w.get("country_code", self.home_cc),
                "address": w.get("address", ""), "postcode": w.get("postcode", ""),
                "manager_id": None, "is_active": True,
                "opened_date": date(int(w.get("opened_year", self.p.start_year - 5)),
                                    r.randint(1, 12), 1),
                "monthly_rent": 0,
                "capacity_sqm": float(w.get("capacity_sqm", 2000)),
                "storage_type": w.get("storage_type", "Raflı"),
                "is_bonded": bool(w.get("is_bonded", False)),
            })
        self._wh = {w["id"]: w for w in self.rows("warehouses")}
        self._wh_by_code = {w["code"]: w["id"] for w in self.rows("warehouses")}
        self._wh_all = [w["id"] for w in self.rows("warehouses")]
        self._wh_fg = self._wh_by_code.get("MAM", self._wh_all[0])
        self._wh_rm = self._wh_by_code.get("HAM", self._wh_all[0])
        self._wh_wip = self._wh_by_code.get("ARA", self._wh_all[0])
        self._wh_de = self._wh_all          # BackOfficeMixin uyumluluğu
        self._wh_tr = self._wh_all

    def gen_work_centers(self):
        r = self.rng.stream("wc")
        for w in self.s["work_centers"]:
            wid = self.nid("work_centers")
            self.add("work_centers", {
                "id": wid, "code": w.get("code", f"IM{wid:02d}"), "name": w["name"],
                "capacity_per_hour": float(w.get("capacity_per_hour", 100)),
                "cost_per_hour": money(float(w.get("cost_per_hour_eur", 22))
                                       * self.try_per("EUR", self._today())),
                "is_active": True,
                "department_id": self._dept_by_name.get(w.get("department", "Üretim")),
                "machine_count": int(w.get("machine_count", 3)),
                "shift_count": int(w.get("shift_count", 3)),
                "area_sqm": float(w.get("area_sqm", 600)),
                "cost_center": w.get("cost_center", f"MM-2{wid:03d}"),
                "target_oee_pct": float(w.get("target_oee_pct", 78)),
                "process_family": w.get("process_family", "Talaşlı İmalat"),
                "is_subcontract": bool(w.get("is_subcontract", False)),
            })
            # saatlik maliyet EUR olarak yazılır; TL karşılığı işlem anında hesaplanır
            self.rows("work_centers")[-1]["_rate_eur"] = float(w.get("cost_per_hour_eur", 22))
            self.rows("work_centers")[-1]["_labor_eur"] = float(w.get("labor_rate_eur", 6.5))
        self._wc = {w["id"]: w for w in self.rows("work_centers")}
        self._wc_by_code = {w["code"]: w["id"] for w in self.rows("work_centers")}
        self._wc_internal = [w["id"] for w in self.rows("work_centers") if not w["is_subcontract"]]

    # ================================================================ personel ==
    def gen_employees(self):
        """Kadro departman bazında seeds'te yazılıdır; böylece organizasyon
        şeması gerçekten bir talaşlı imalat fabrikasına benzer: ağırlık üretim
        operatörlerinde, ardından kalite ve bakımda."""
        r = self.rng.stream("emp")
        today = self._today()
        try_eur = self.try_per("EUR", today)
        self.salespeople, self.technicians, self.operators = [], [], []
        self.planners, self.quality_staff, self.engineers, self.buyers = [], [], [], []
        self._emp_by_dept = {}
        managers = {}
        shifts = self.t.get("shifts", ["1. Vardiya", "2. Vardiya", "3. Vardiya"])
        shift_w = self.t.get("shift_weights", [42, 34, 24])
        wc_pool = list(self._wc_internal)

        for dept in self.rows("departments"):
            spec = self._dept_seed.get(dept["name"], {})
            for role in spec.get("roles", []):
                for _ in range(int(role.get("count", 1))):
                    eid = self.nid("employees")
                    fn, ln = locales.person(r, "tr")
                    hire = self._hire_date(r, role)
                    gross_eur = float(role["annual_gross_eur"]) * r.jitter(1.0, 0.085)
                    gross_try = money(gross_eur * try_eur)
                    is_shift = bool(role.get("shift", False))
                    city, region, country, iso2, phone_cc, _c, _e = locales.location(
                        r, [l for l in locales.TR_LOCATIONS if l[3] == "TR"])
                    if r.chance(0.86):
                        city, region = "Gaziantep", "Gaziantep"
                    self.add("employees", {
                        "id": eid, "first_name": fn, "last_name": ln,
                        "full_name": f"{fn} {ln}",
                        "email": f"{self._ascii(fn)}.{self._ascii(ln)}@{self.domain}".lower(),
                        "department_id": dept["id"], "role": role["title"],
                        "hire_date": hire, "salary": gross_try, "is_active": True,
                        "employee_no": f"PRS-{eid:04d}", "country": self.home_country,
                        "country_code": self.home_cc, "city": city,
                        "work_location": "Gaziantep 2. OSB Fabrika",
                        "warehouse_id": None,
                        "employment_type": role.get("employment_type", "Tam Zamanlı"),
                        "manager_id": None, "currency": self.base_ccy,
                        "annual_gross": gross_try,
                        "employer_cost_rate": 0.2275, "weekly_hours": 45.0,
                        "termination_date": None,
                        "gender": "K" if fn in locales.TR_FIRST_F else "E",
                        "birth_year": hire.year - r.randint(21, 52),
                        "phone": locales.phone_for(r, "90"),
                        "shift": (r.weighted(shifts, shift_w) if is_shift else "Normal Mesai"),
                        "job_family": role.get("job_family", "Destek"),
                        "skill_level": role.get("skill_level", "Uzman"),
                        "education": r.weighted(
                            ["İlköğretim", "Lise", "Endüstri Meslek Lisesi", "Ön Lisans",
                             "Lisans", "Yüksek Lisans"],
                            role.get("education_weights", [6, 22, 30, 18, 20, 4])),
                        "marital_status": r.weighted(["Evli", "Bekar", "Boşanmış"], [62, 33, 5]),
                        "children_count": r.weighted([0, 1, 2, 3, 4], [30, 26, 30, 11, 3]),
                        "leave_entitlement_days": 14 if (today - hire).days < 1825 else (
                            20 if (today - hire).days < 5475 else 26),
                        "overtime_eligible": bool(role.get("overtime_eligible", is_shift)),
                        "cost_center": dept["cost_center"],
                        # operatör kendi proses ailesindeki iş merkezine bağlanır;
                        # aksi halde otomat torna operatörü taşlama tezgahında görünür
                        "work_center_id": self._wc_for_role(r, role, wc_pool),
                        "union_member": bool(is_shift and r.chance(0.34)),
                        "monthly_gross_try": money(gross_try / 12.0),
                        "seniority_years": round((today - hire).days / 365.25, 2),
                    })
                    self._emp_by_dept.setdefault(dept["name"], []).append(eid)
                    if role.get("is_sales"):
                        self.salespeople.append(eid)
                    if role.get("is_technician"):
                        self.technicians.append(eid)
                    if role.get("is_operator"):
                        self.operators.append(eid)
                    if role.get("is_planner"):
                        self.planners.append(eid)
                    if role.get("is_quality"):
                        self.quality_staff.append(eid)
                    if role.get("is_engineer"):
                        self.engineers.append(eid)
                    if role.get("is_buyer"):
                        self.buyers.append(eid)
                    if role.get("is_manager"):
                        managers[dept["name"]] = eid

        self._add_leavers_tr(r, try_eur)

        for e in self.rows("employees"):
            dname = self._dept_row[e["department_id"]]["name"]
            mgr = managers.get(dname)
            e["manager_id"] = mgr if mgr and mgr != e["id"] else None
        for dname, mid in managers.items():
            self._dept_row[self._dept_by_name[dname]]["manager_id"] = mid
        wh_pool = self._emp_by_dept.get("Depo ve Sevkiyat", []) or self.operators
        for i, w in enumerate(self.rows("warehouses")):
            w["manager_id"] = wh_pool[i % len(wh_pool)] if wh_pool else None

        fallback = [self.rows("employees")[0]["id"]]
        for attr in ("salespeople", "technicians", "operators", "planners",
                     "quality_staff", "engineers", "buyers"):
            if not getattr(self, attr):
                setattr(self, attr, list(fallback))
        self._emp = {e["id"]: e for e in self.rows("employees")}
        self._active_emp = [e for e in self.rows("employees") if e["is_active"]]

    def _wc_for_role(self, r, role, wc_pool):
        if role.get("job_family") not in ("Üretim", "Bakım", "Kalite") or not wc_pool:
            return None
        fams = role.get("wc_families")
        if fams:
            cand = [w for w in wc_pool if self._wc[w]["process_family"] in fams]
            if cand:
                return r.choice(cand)
        return r.choice(wc_pool)

    def _add_leavers_tr(self, r, try_eur):
        """Ayrılmış personel. Olmazsa bordro geçmişinde hiç devir görünmez ve
        ilk yıllar bugünkü kadroyla çalışmış gibi olur."""
        churn = float(self.t.get("historical_churn_ratio", 0.31))
        current = list(self.rows("employees"))
        today = self._today()
        for _ in range(int(round(len(current) * churn))):
            tmpl = r.choice(current)
            eid = self.nid("employees")
            fn, ln = locales.person(r, "tr")
            hire = self._hire_date(r, {})
            term = add_days(hire, r.randint(200, 2100))
            if term >= today:
                term = add_days(today, -r.randint(15, 800))
            if term <= hire:
                continue
            gross = money(float(tmpl["annual_gross"]) * r.jitter(0.93, 0.13))
            row = dict(tmpl)
            row.update({
                "id": eid, "first_name": fn, "last_name": ln, "full_name": f"{fn} {ln}",
                "email": f"{self._ascii(fn)}.{self._ascii(ln)}.{eid}@{self.domain}".lower(),
                "hire_date": hire, "salary": gross, "annual_gross": gross,
                "monthly_gross_try": money(gross / 12.0),
                "is_active": False, "termination_date": term,
                "employee_no": f"PRS-{eid:04d}",
                "gender": "K" if fn in locales.TR_FIRST_F else "E",
                "birth_year": hire.year - r.randint(21, 52),
                "phone": locales.phone_for(r, "90"),
                "seniority_years": round((term - hire).days / 365.25, 2),
            })
            self.add("employees", row)
            self._emp_by_dept.setdefault(
                self._dept_row[row["department_id"]]["name"], []).append(eid)

    def _hire_date(self, r, role_spec):
        founded = self.s["company"].get("founded_year", self.p.start_year - 12)
        years = list(range(founded, self.p.end_year() + 1))
        weights = self.t.get("hire_year_weights")
        if not weights or len(weights) != len(years):
            weights = [26, 14] + [max(3, int(60 / max(1, len(years) - 2)))] * (len(years) - 2)
        y = r.weighted(years, weights[:len(years)])
        return min(random_date_in_month(r, y, r.randint(1, 12)), self._today())

    @staticmethod
    def _ascii(s: str) -> str:
        table = str.maketrans({
            "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c",
            "Ç": "c", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "â": "a", "î": "i",
            "û": "u", "É": "e", "é": "e",
        })
        return "".join(ch for ch in s.translate(table) if ch.isalnum() or ch in "._-")

    # ================================================================ tezgahlar ==
    def gen_machines(self):
        r = self.rng.stream("mach")
        today = self._today()
        try_eur = self.try_per("EUR", today)
        for spec in self.s.get("shop_machines", []):
            wc_id = self._wc_by_code.get(spec.get("work_center_code")) or (
                self._wc_internal[0] if self._wc_internal else None)
            wc = self._wc.get(wc_id, {})
            for k in range(int(spec.get("count", 1))):
                mid = self.nid("machines")
                year = int(spec.get("year_min", self.p.start_year - 8))
                ymax = int(spec.get("year_max", self.p.end_year() - 1))
                installed = r.randint(min(year, ymax), ymax)
                comm = random_date_in_month(r, installed, r.randint(1, 12))
                self.add("machines", {
                    "id": mid, "code": f"TZG-{mid:03d}",
                    "name": f"{spec['manufacturer']} {spec['model']}"
                            + (f" #{k+1}" if int(spec.get("count", 1)) > 1 else ""),
                    "machine_type": spec["machine_type"], "work_center_id": wc_id,
                    "department_id": wc.get("department_id"),
                    "manufacturer": spec["manufacturer"], "model": spec["model"],
                    "control_system": r.choice(spec.get("controls", ["Fanuc 0i-TF"])),
                    "axis_count": int(spec.get("axes", 3)), "year_installed": installed,
                    "commissioned_date": min(comm, today), "fixed_asset_id": None,
                    "warehouse_id": None, "power_kw": float(spec.get("power_kw", 22)),
                    "max_bar_dia_mm": spec.get("max_bar_dia_mm"),
                    "max_part_dia_mm": spec.get("max_part_dia_mm"),
                    "spindle_count": int(spec.get("spindles", 1)),
                    "tool_capacity": int(spec.get("tool_capacity", 12)),
                    "has_bar_feeder": bool(spec.get("bar_feeder", False)),
                    "has_robot_loading": bool(spec.get("robot", False)),
                    "hourly_rate": money(float(spec.get("hourly_rate_eur", 20)) * try_eur),
                    "capacity_per_hour": float(spec.get("capacity_per_hour", 60)),
                    "target_oee_pct": float(spec.get("target_oee_pct", 78)),
                    "status": r.weighted(["Aktif", "Aktif", "Aktif", "Bakımda", "Yedek"],
                                         [70, 15, 8, 4, 3]),
                    "serial_no": f"{spec['manufacturer'][:3].upper()}-{installed}"
                                 f"{r.randint(1000, 9999)}",
                    "notes": spec.get("notes", ""),
                })
                self.rows("machines")[-1]["_rate_eur"] = float(spec.get("hourly_rate_eur", 20))
                self.rows("machines")[-1]["_cost_eur"] = float(spec.get("cost_eur", 180000))
                self.rows("machines")[-1]["_asset_category"] = spec.get(
                    "asset_category", "Tezgah ve Üretim Makinaları")
        self._mach = {m["id"]: m for m in self.rows("machines")}
        self._mach_by_wc = {}
        for m in self.rows("machines"):
            self._mach_by_wc.setdefault(m["work_center_id"], []).append(m["id"])
        for wc in self.rows("work_centers"):
            wc["machine_count"] = len(self._mach_by_wc.get(wc["id"], []))

    # ================================================================ müşteriler ==
    def gen_customers(self):
        r = self.rng.stream("cust")
        eu_pool = [l for l in locales.EU_LOCATIONS if l[6]]
        tr_pool = locales.TR_LOCATIONS
        near_pool = locales.NEAR_EXPORT_LOCATIONS
        by_cc = {}
        for loc in locales.EU_LOCATIONS + tr_pool + near_pool:
            by_cc.setdefault(loc[3], []).append(loc)
        industries = self.t.get("customer_industries", ["Otomotiv Tier-1"])
        seeded = {c["name"]: c for c in self.s.get("customers", [])}
        programs = self.s.get("customer_programs", [])

        for raw in self.s["customer_names"]:
            cid = self.nid("customers")
            meta = seeded.get(raw, {})
            cc = meta.get("country_code")
            if cc and by_cc.get(cc):
                loc = locales.location(r, by_cc[cc])
                nm = raw
            else:
                loc = locales.location(r, tr_pool)
                nm = raw if raw.rstrip().endswith((".", "Ş.", "A.Ş.")) else (
                    f"{raw} {locales.tr_company_suffix(r)}")
            city, region, country, iso2, phone_cc, cur, in_eu = loc
            is_export = iso2 != self.home_cc
            if not is_export:
                ccy = self.base_ccy if r.chance(0.72) else "EUR"
            elif in_eu:
                ccy = "EUR" if r.chance(0.94) else "USD"
            elif iso2 == "GB":
                ccy = "GBP" if r.chance(0.6) else "EUR"
            else:
                ccy = "USD" if r.chance(0.76) else "EUR"
            seg = meta.get("segment") or r.weighted(
                ["Küçük Ölçekli", "Orta Ölçekli", "Kurumsal / OEM"], [40, 39, 21])
            climit_eur = {"Küçük Ölçekli": 45000, "Orta Ölçekli": 260000,
                          "Kurumsal / OEM": 1400000}[seg]
            created = meta.get("customer_since")
            created = (date.fromisoformat(created) if created
                       else self._spread_date(r, before_start_ok=True))
            abc = r.weighted(["A", "B", "C"], [18, 32, 50])
            self.add("customers", {
                "id": cid, "name": nm, "segment": seg,
                "address": (locales.street_for(r, iso2) if iso2 != "TR"
                            else r.choice(locales.GAZIANTEP_STREETS + locales.TR_STREETS)
                                 + f" No:{r.randint(1, 180)}"),
                "city": city, "state": region, "country": country,
                "email": f"satinalma@{self._co_domain(nm)}",
                "phone": locales.phone_for(r, phone_cc),
                "credit_limit": money(climit_eur * self.try_per("EUR", self._today())
                                      * r.jitter(1.0, 0.3)),
                "created_at": created, "country_code": iso2,
                "postcode": locales.postcode_for(r, iso2), "currency": ccy,
                "payment_terms_days": meta.get("payment_terms_days") or r.weighted(
                    self.t.get("payment_terms_days", [30, 60, 90]), [16, 20, 30, 12, 16, 6]),
                "incoterm": r.choice(self.t["incoterms_export"] if is_export
                                     else self.t["incoterms_domestic"]),
                "tax_regime": ("Yurt İçi (KDV %20)" if not is_export else
                               ("İhracat - AB / Gümrük Birliği (A.TR)" if in_eu
                                else "İhracat - Üçüncü Ülke")),
                "vat_number": (f"{r.randint(1000000000, 9999999999)}" if iso2 == "TR"
                               else f"{iso2}{r.randint(100000000, 999999999)}"),
                "industry": meta.get("industry") or r.choice(industries),
                "account_manager_id": r.choice(self.salespeople),
                "is_export": is_export, "is_intra_eu": bool(in_eu),
                "contact_name": ("%s %s" % locales.person(r, "tr") if iso2 == "TR"
                                 else "%s %s" % locales.person(r, "de")),
                "first_order_date": None,
                "status": r.weighted(["Aktif", "Aktif", "Pasif", "Potansiyel"], [72, 14, 9, 5]),
                "customer_since": created, "abc_class": abc,
                "edi_enabled": bool(seg == "Kurumsal / OEM" and r.chance(0.72)),
                "quality_agreement": bool(r.chance(0.66)),
                "supplier_code": f"{iso2}-{r.randint(10000, 99999)}",
                "region": ("Yurt İçi" if not is_export else
                           ("Avrupa Birliği" if in_eu else
                            ("Ortadoğu / Körfez" if iso2 in ("IQ", "IR", "SA", "AE", "QA",
                                                             "KW", "JO", "EG")
                             else ("Kafkasya / Orta Asya" if iso2 in ("AZ", "GE", "UZ", "KZ", "TM")
                                   else ("Balkanlar" if iso2 in ("RS", "MK", "BA", "AL", "XK")
                                         else "Diğer İhracat"))))),
                "ppm_target": r.choice([10, 25, 25, 50, 50, 100, 200]),
                "_weight": meta.get("weight"),
                "_program": meta.get("program") or (r.choice(programs) if programs else None),
            })
        self._cust = {c["id"]: c for c in self.rows("customers")}
        seg_w = {"Küçük Ölçekli": 1.0, "Orta Ölçekli": 5.0, "Kurumsal / OEM": 26.0}
        self._customer_picker = WeightedPicker(
            [c["id"] for c in self.rows("customers")],
            [(c["_weight"] if c["_weight"] else seg_w[c["segment"]])
             * (0.25 if c["status"] in ("Pasif", "Potansiyel") else 1.0)
             * r.lognormal(1.0, 0.55) for c in self.rows("customers")],
            self.rng.stream("cust_pick"))
        self._export_customers = [c["id"] for c in self.rows("customers") if c["is_export"]]
        self._domestic_customers = [c["id"] for c in self.rows("customers") if not c["is_export"]]
        self._export_picker = self._sub_picker(self._export_customers, seg_w, r, "exp_pick")
        self._domestic_picker = self._sub_picker(self._domestic_customers, seg_w, r, "dom_pick")

    def _sub_picker(self, ids, seg_w, r, stream):
        if not ids:
            return None
        return WeightedPicker(
            ids, [(self._cust[i]["_weight"] if self._cust[i]["_weight"]
                   else seg_w[self._cust[i]["segment"]])
                  * (0.25 if self._cust[i]["status"] in ("Pasif", "Potansiyel") else 1.0)
                  * r.lognormal(1.0, 0.5) for i in ids],
            self.rng.stream(stream))

    @staticmethod
    def _co_domain(name: str) -> str:
        keep = "".join(ch if (ch.isalnum() or ch == " ") else " " for ch in name.lower())
        table = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ç": "c", "ü": "u", "ö": "o"})
        parts = keep.translate(table).split()
        skip = {"san", "tic", "a", "ş", "ltd", "şti", "sti", "ve", "sanayi", "ticaret",
                "gmbh", "sarl", "srl", "sa", "bv", "co", "ltd."}
        head = next((p for p in parts if p not in skip and len(p) > 2), "firma")
        return f"{head}.example.com"

    # ================================================================ tedarikçi ==
    def gen_vendors(self):
        r = self.rng.stream("vend")
        types = self.t.get("vendor_types", ["Çelik Servis Merkezi"])
        tr_pool = locales.TR_LOCATIONS
        eu_pool = [l for l in locales.EU_LOCATIONS if l[6]]
        by_cc = {}
        for loc in locales.EU_LOCATIONS + tr_pool + locales.NEAR_EXPORT_LOCATIONS:
            by_cc.setdefault(loc[3], []).append(loc)
        seeded = {v["name"]: v for v in self.s.get("vendors", [])}
        for raw in self.s["vendor_names"]:
            vid = self.nid("vendors")
            meta = seeded.get(raw, {})
            cc = meta.get("country_code")
            if cc and by_cc.get(cc):
                loc = locales.location(r, by_cc[cc])
                nm = raw
            else:
                loc = locales.location(r, tr_pool)
                nm = raw if raw.rstrip().endswith((".", "Ş.", "A.Ş.")) else (
                    f"{raw} {locales.tr_company_suffix(r)}")
            city, region, country, iso2, phone_cc, cur, in_eu = loc
            vtype = meta.get("type") or r.choice(types)
            ccy = (self.base_ccy if iso2 == "TR" and r.chance(0.78) else
                   ("EUR" if (in_eu or r.chance(0.6)) else "USD"))
            self.add("vendors", {
                "id": vid, "name": nm, "category": vtype,
                "address": (r.choice(locales.GAZIANTEP_STREETS + locales.TR_STREETS)
                            + f" No:{r.randint(1, 180)}" if iso2 == "TR"
                            else locales.street_for(r, iso2)),
                "city": city, "state": region, "country": country,
                "email": f"satis@{self._co_domain(nm)}",
                "phone": locales.phone_for(r, phone_cc),
                "lead_time_days": int(meta.get("lead_time_days")
                                      or r.choice([2, 3, 5, 7, 10, 14, 21, 30, 45])),
                "created_at": self._spread_date(r, before_start_ok=True),
                "country_code": iso2, "postcode": locales.postcode_for(r, iso2),
                "currency": ccy, "vendor_type": vtype,
                "payment_terms_days": r.weighted([0, 30, 45, 60, 90, 120],
                                                 [10, 22, 20, 26, 16, 6]),
                "vat_number": (f"{r.randint(1000000000, 9999999999)}" if iso2 == "TR"
                               else f"{iso2}{r.randint(100000000, 999999999)}"),
                "rating": round(r.jitter(4.05, 0.17), 2),
                "contact_name": ("%s %s" % locales.person(r, "tr") if iso2 == "TR"
                                 else "%s %s" % locales.person(r, "de")),
                "status": r.weighted(["Aktif", "Aktif", "Pasif"], [82, 10, 8]),
                "is_approved": r.chance(0.9), "approval_date": self._spread_date(r, True),
                "quality_score": round(r.jitter(93.0, 0.07), 2),
                "otd_score": round(min(100.0, r.jitter(91.0, 0.09)), 2),
                "iso_certified": r.chance(0.74),
                "region": "Yurt İçi" if iso2 == "TR" else ("Avrupa" if in_eu else "Diğer"),
            })
        self._vend = {v["id"]: v for v in self.rows("vendors")}
        self._vend_by_type = {}
        for v in self.rows("vendors"):
            self._vend_by_type.setdefault(v["vendor_type"], []).append(v["id"])

    def _vpool(self, *types):
        out = []
        for t in types:
            out.extend(self._vend_by_type.get(t, []))
        return out or list(self._vend)

    def gen_carriers(self):
        r = self.rng.stream("carrier")
        for c in self.s.get("carriers", []):
            self.add("carriers", {
                "id": self.nid("carriers"), "name": c["name"],
                "carrier_type": c.get("type", "Nakliye Firması"),
                "mode": c.get("mode", "Karayolu"),
                "country": c.get("country", self.home_country),
                "city": c.get("city", "Gaziantep"), "scac": c.get("scac", ""),
                "is_customs_broker": bool(c.get("is_customs_broker", False)),
                "email": f"operasyon@{self._co_domain(c['name'])}",
                "phone": locales.phone_for(r, c.get("phone_cc", "90")),
            })
        self._carriers_by_mode = {}
        for c in self.rows("carriers"):
            self._carriers_by_mode.setdefault(c["mode"], []).append(c["id"])
        self._brokers = [c["id"] for c in self.rows("carriers") if c["is_customs_broker"]]

    # =========================================================== hammadde/ürün ==
    def gen_raw_materials(self):
        r = self.rng.stream("raw")
        today = self._today()
        try_eur = self.try_per("EUR", today)
        for base in self.s.get("raw_materials", []):
            rid = self.nid("raw_materials")
            pool = self._vpool(*(base.get("vendor_types") or ["Çelik Servis Merkezi"]))
            price_eur = float(base["price_eur_per_unit"])
            self.add("raw_materials", {
                "id": rid, "code": base.get("code", f"HM-{rid:04d}"), "name": base["name"],
                "category": base.get("category", "Metal"), "uom": base.get("uom", "kg"),
                "unit_cost": round(price_eur * try_eur, 4),
                "vendor_id": r.choice(pool) if pool else None,
                "material_grade": base.get("grade", ""), "standard": base.get("standard", ""),
                "form": base.get("form", "Çubuk"),
                "diameter_mm": base.get("diameter_mm"),
                "wall_thickness_mm": base.get("wall_thickness_mm"),
                "density_kg_dm3": base.get("density", 7.85),
                "unit_cost_eur": price_eur,
                "pricing_currency": base.get("pricing_currency", "EUR"),
                "moq": base.get("moq", 500), "lead_time_days": base.get("lead_time_days", 21),
                "is_customer_supplied": bool(base.get("customer_supplied", False)),
                "origin_country": base.get("origin", "TR"),
                "hs_code": base.get("hs_code", "7228.30"),
            })
            self.rows("raw_materials")[-1]["_price_eur"] = price_eur
            self.rows("raw_materials")[-1]["_group"] = base.get("group", "metal")
        self._rm = {m["id"]: m for m in self.rows("raw_materials")}
        self._rm_by_group = {}
        for m in self.rows("raw_materials"):
            self._rm_by_group.setdefault(m["_group"], []).append(m["id"])
        self._rm_by_grade = {}
        for m in self.rows("raw_materials"):
            if m["material_grade"]:
                self._rm_by_grade.setdefault(m["material_grade"], []).append(m["id"])

    _VARIANTS = ["Ø8", "Ø10", "Ø12", "Ø14", "Ø16", "Ø18", "Ø20", "Ø22", "Ø25", "Ø28",
                 "Ø30", "Ø32", "Ø35", "Ø40", "Ø45", "Ø50", "M6", "M8", "M10", "M12",
                 "M14", "M16", "M18", "M20", "1/4\"", "3/8\"", "1/2\"", "3/4\"",
                 "Tip A", "Tip B", "Tip C", "Kısa Tip", "Uzun Tip", "Sol Diş", "Sağ Diş",
                 "Rev.B", "Rev.C", "Rev.D"]

    def gen_products(self):
        """Parça kataloğu. Fiyat ve maliyetler EUR referansında tutulur; ürün
        tablosundaki TL değerleri dönem sonu kuruna göre yazılır."""
        r = self.rng.stream("prod")
        today = self._today()
        try_eur = self.try_per("EUR", today)
        try_usd = self.try_per("USD", today)
        seeded = self.s["products"]
        cust_ids = [c["id"] for c in self.rows("customers")]
        oem_ids = [c["id"] for c in self.rows("customers")
                   if c["segment"] == "Kurumsal / OEM"] or cust_ids
        used_names = set()
        n = max(self.p.n_products, len(seeded))
        for i in range(n):
            base = seeded[i % len(seeded)]
            pid = self.nid("products")
            nm = base["name"]
            if i >= len(seeded):
                nm = f"{nm} {r.choice(self._VARIANTS)}"
            guard = 0
            while nm in used_names and guard < 40:
                guard += 1
                nm = f"{base['name']} {r.choice(self._VARIANTS)}-{r.randint(2, 99)}"
            used_names.add(nm)

            lo, hi = float(base["price_eur_min"]), float(base["price_eur_max"])
            price_eur = round(lo + r.rand() * max(hi - lo, 0.001), 4)
            margin = min(0.68, max(0.24, r.jitter(float(base.get("margin_pct", 49.5)) / 100.0,
                                                  0.13)))
            direct_eur = price_eur * (1 - margin)
            mix = base.get("cost_mix", {})
            m_sh = float(mix.get("material", 0.61))
            l_sh = float(mix.get("labor", 0.20))
            s_sh = float(mix.get("subcontract", 0.13))
            t_sh = max(0.02, 1.0 - m_sh - l_sh - s_sh)
            has_sub = bool(base.get("subcontract", True)) and s_sh > 0.01
            if not has_sub:
                m_sh, l_sh, t_sh = m_sh + s_sh * 0.5, l_sh + s_sh * 0.3, t_sh + s_sh * 0.2
                s_sh = 0.0
            mat = round(direct_eur * m_sh, 5)
            lab = round(direct_eur * l_sh, 5)
            sub = round(direct_eur * s_sh, 5)
            tool = round(direct_eur - mat - lab - sub, 5)
            mach_eur = round(price_eur * float(base.get("machine_alloc_pct", 13.5)) / 100.0, 5)
            ovh_eur = round(price_eur * float(base.get("overhead_alloc_pct", 9.5)) / 100.0, 5)

            owner = r.choice(oem_ids) if r.chance(0.62) else r.choice(cust_ids)
            row = {
                "id": pid, "sku": base.get("sku_prefix", "PRC") + f"-{pid:05d}",
                "name": nm[:120], "category": base["category"],
                "uom": base.get("uom", "adet"),
                "unit_cost": round(direct_eur * try_eur, 4),
                "list_price": round(price_eur * try_eur, 4),
                "is_active": r.chance(0.93),
                "created_at": self._spread_date(r, before_start_ok=True),
                "item_type": "Mamul", "subcategory": base.get("subcategory", base["category"]),
                "brand": self.s["company"]["name"], "condition": "Yeni",
                "weight_kg": float(base.get("net_weight_kg", 0.3)),
                "hs_code": base.get("hs_code", "8483.90"), "origin_country": "TR",
                "lead_time_days": int(base.get("lead_time_days", 21)),
                "is_stocked": True,
                "reorder_point": r.choice([0, 500, 1000, 2000, 5000]),
                "target_margin_pct": round(margin * 100, 2),
                "drawing_no": f"TR-{r.randint(100000, 999999)}",
                "revision": r.choice(["A", "B", "B", "C", "C", "D", "E"]),
                "customer_id": owner, "program_name": self._cust[owner]["_program"],
                "material_grade": base.get("material_grade", "11SMn30"),
                "net_weight_kg": float(base.get("net_weight_kg", 0.3)),
                "gross_weight_kg": round(float(base.get("net_weight_kg", 0.3)) * 1.06, 4),
                "raw_weight_kg": round(float(base.get("net_weight_kg", 0.3))
                                       * float(base.get("material_yield_factor", 1.45)), 4),
                "surface_treatment": base.get("surface_treatment", "Yok"),
                "tolerance_class": base.get("tolerance_class", "IT8"),
                "is_safety_part": bool(base.get("is_safety_part", False)),
                "annual_volume": None,
                "std_cost_material": round(mat * try_eur, 4),
                "std_cost_labor": round(lab * try_eur, 4),
                "std_cost_machine": round(mach_eur * try_eur, 4),
                "std_cost_tooling": round(tool * try_eur, 4),
                "std_cost_subcontract": round(sub * try_eur, 4),
                "std_cost_overhead": round(ovh_eur * try_eur, 4),
                "std_cost_total": round((mat + lab + mach_eur + tool + sub + ovh_eur)
                                        * try_eur, 4),
                "unit_cost_eur": round(direct_eur, 5),
                "list_price_eur": price_eur,
                "list_price_usd": round(price_eur * try_eur / try_usd, 4),
                "pricing_currency": base.get("pricing_currency", "EUR"),
                "cavity_count": 1,
                "operation_count": None,
            }
            self.add("products", row)
            row["_price_eur"] = price_eur
            row["_mat_eur"] = mat
            row["_lab_eur"] = lab
            row["_sub_eur"] = sub
            row["_tool_eur"] = tool
            row["_direct_eur"] = round(mat + lab + sub + tool, 5)
            row["_lot_min"] = int(base.get("lot_min", 500))
            row["_lot_max"] = int(base.get("lot_max", 5000))
            row["_routing"] = base.get("routing", "genel")
            row["_cycle_scale"] = float(base.get("cycle_scale", 1.0))
            row["_popularity"] = float(base.get("popularity", 1.0))
            row["_rm_group"] = base.get("rm_group", "celik_cubuk")
            row["_family"] = base.get("family", base["category"])
        self._prod = {p["id"]: p for p in self.rows("products")}
        self._product_picker = WeightedPicker(
            [p["id"] for p in self.rows("products")],
            [p["_popularity"] * (0.2 if not p["is_active"] else 1.0) * r.lognormal(1.0, 0.85)
             for p in self.rows("products")],
            self.rng.stream("prod_pick"))
        self._product_by_id = self._prod

    def gen_bom(self):
        """Reçete: bir ana hammadde (parça malzeme kalitesine göre) ve
        ambalaj / yardımcı malzemeler."""
        r = self.rng.stream("bom")
        pack = self._rm_by_group.get("ambalaj", [])
        chem = self._rm_by_group.get("kimyasal", [])
        comp = self._rm_by_group.get("komponent", [])
        for p in self.rows("products"):
            bid = self.nid("bom")
            self.add("bom", {
                "id": bid, "product_id": p["id"],
                "name": f"{p['sku']} Ürün Reçetesi", "version": f"v{r.randint(1, 4)}",
                "output_qty": 1, "is_active": True,
            })
            pool = (self._rm_by_grade.get(p["material_grade"])
                    or self._rm_by_group.get(p["_rm_group"])
                    or list(self._rm))
            main = r.choice(pool)
            self.add("bom_lines", {
                "id": self.nid("bom_lines"), "bom_id": bid, "raw_material_id": main,
                "qty_per": round(p["raw_weight_kg"], 4),
                "scrap_pct": round(r.jitter(2.2, 0.6), 2),
            })
            lines = [(main, p["raw_weight_kg"])]
            if pack:
                pk = r.choice(pack)
                self.add("bom_lines", {
                    "id": self.nid("bom_lines"), "bom_id": bid, "raw_material_id": pk,
                    "qty_per": round(r.jitter(0.012, 0.5), 5), "scrap_pct": 0.5,
                })
                lines.append((pk, 0.012))
            if chem and r.chance(0.55):
                ch = r.choice(chem)
                self.add("bom_lines", {
                    "id": self.nid("bom_lines"), "bom_id": bid, "raw_material_id": ch,
                    "qty_per": round(r.jitter(0.004, 0.6), 5), "scrap_pct": 0.0,
                })
                lines.append((ch, 0.004))
            if comp and r.chance(0.18):
                cp = r.choice(comp)
                self.add("bom_lines", {
                    "id": self.nid("bom_lines"), "bom_id": bid, "raw_material_id": cp,
                    "qty_per": 1, "scrap_pct": 0.3,
                })
                lines.append((cp, 1))
            p["_bom_id"] = bid
            p["_bom_lines"] = lines
        self._bom_by_product = {b["product_id"]: b["id"] for b in self.rows("bom")}

    # =================================================================== rota ==
    def gen_routings(self):
        """Operasyon rotası. İşleme süreleri parçanın tezgah maliyeti payından
        türetilir; böylece toplam tezgah saati ile makine parkı kapasitesi
        kendiliğinden tutarlı olur."""
        r = self.rng.stream("route")
        today = self._today()
        try_eur = self.try_per("EUR", today)
        ops = {o["code"]: o for o in self.s.get("operations", [])}
        templates = self.s.get("routing_templates", {})
        default_tpl = list(templates.values())[0] if templates else []

        for p in self.rows("products"):
            tpl = templates.get(p["_routing"], default_tpl)
            steps = [ops[c] for c in tpl if c in ops]
            if not steps:
                continue
            machining = [o for o in steps if not o.get("is_subcontract")]
            weights = [float(o.get("time_weight", 1.0)) for o in machining]
            wsum = sum(weights) or 1.0
            avg_rate = (sum(float(o.get("machine_rate_eur", 18)) * w
                            for o, w in zip(machining, weights)) / wsum) or 18.0
            total_sec = max(4.0, (p["_mat_eur"] * 0 + p["std_cost_machine"] / try_eur)
                            / avg_rate * 3600.0)
            n_sub = sum(1 for o in steps if o.get("is_subcontract"))
            tool_per_op = (p["_tool_eur"] * try_eur) / max(1, len(machining))
            p["_ops"] = []
            op_no = 0
            for o in steps:
                op_no += 10
                rid = self.nid("routings")
                is_sub = bool(o.get("is_subcontract"))
                wc_id = self._wc_by_code.get(o["wc_code"])
                mach_pool = self._mach_by_wc.get(wc_id, [])
                if is_sub:
                    vpool = self._vpool(o.get("vendor_type", "Isıl İşlem (Fason)"))
                    sub_price = round((p["_sub_eur"] / max(1, n_sub)) * r.jitter(1.0, 0.08), 5)
                    cyc = 0.0
                    setup = 0.0
                else:
                    vpool = []
                    sub_price = None
                    w = float(o.get("time_weight", 1.0)) / wsum
                    cyc = round(max(1.5, total_sec * w * r.jitter(1.0, 0.09)), 3)
                    setup = round(float(o.get("setup_min", 25)) * r.jitter(1.0, 0.22), 2)
                lab_eur = float(o.get("labor_rate_eur", 6.2))
                mac_eur = float(o.get("machine_rate_eur", 18))
                row = {
                    "id": rid, "product_id": p["id"], "version": p["revision"],
                    "operation_no": op_no, "operation_name": o["name"],
                    "operation_type": o.get("type", "Talaşlı İmalat"),
                    "work_center_id": wc_id,
                    "machine_id": (r.choice(mach_pool) if mach_pool and not is_sub else None),
                    "setup_minutes": setup, "cycle_time_sec": cyc,
                    "pieces_per_hour": round(3600.0 / cyc, 2) if cyc > 0 else None,
                    "std_labor_rate": money(lab_eur * try_eur),
                    "std_machine_rate": money(mac_eur * try_eur),
                    "tooling_cost_per_part": (0 if is_sub
                                              else round(tool_per_op * r.jitter(1.0, 0.2), 4)),
                    "is_subcontract": is_sub,
                    "subcontract_vendor_id": (r.choice(vpool) if vpool else None),
                    "subcontract_unit_price": sub_price,
                    "subcontract_currency": "EUR" if is_sub else None,
                    "scrap_pct": round(r.jitter(float(o.get("scrap_pct", 0.6)), 0.5), 3),
                    "is_active": True,
                    "notes": o.get("notes", ""),
                }
                self.add("routings", row)
                row["_labor_eur"] = lab_eur
                row["_machine_eur"] = mac_eur
                row["_sub_process"] = o.get("sub_process", "")
                row["_operators_per_machine"] = float(o.get("operators_per_machine", 0.3))
                p["_ops"].append(row)
            p["operation_count"] = len(p["_ops"])
        self._routing_by_product = {}
        for rt in self.rows("routings"):
            self._routing_by_product.setdefault(rt["product_id"], []).append(rt)

    # ============================================================ fiyat listesi ==
    def gen_price_list(self):
        """Yıllık fiyat anlaşmaları. TL fiyatı her yıl kur + reel zam kadar
        artar; EUR fiyatı ise yalnızca reel zam kadar."""
        r = self.rng.stream("price")
        a_customers = [c for c in self.rows("customers") if c["abc_class"] == "A"]
        for p in self.rows("products"):
            for yi in range(self.p.years):
                year = self.p.start_year + yi
                d = date(year, 1, 1)
                if d < self.start_date:
                    d = self.start_date
                drift = self._drift(d, self.real_price_drift)
                eur_price = round(p["_price_eur"] * drift, 4)
                try_price = round(eur_price * self.try_per("EUR", d), 4)
                usd_price = round(try_price * self.fx("USD", d), 4)
                self.add("price_list", {
                    "id": self.nid("price_list"), "product_id": p["id"],
                    "valid_from": date(year, 1, 1),
                    "valid_to": date(year, 12, 31), "price": try_price,
                    "currency": self.base_ccy, "price_try": try_price,
                    "price_eur": eur_price, "price_usd": usd_price,
                    "customer_id": p["customer_id"],
                    "min_qty": r.choice([1, 500, 1000, 2000, 5000]),
                    "agreement_no": f"FA-{year}-{p['customer_id'] or 0:04d}",
                    "price_type": "Yıllık Fiyat Anlaşması",
                })

    # ============================================================= numune onayı ==
    def gen_part_approvals(self):
        r = self.rng.stream("ppap")
        today = self._today()
        levels = ["Seviye 1", "Seviye 2", "Seviye 3", "Seviye 4", "Seviye 5"]
        for p in self.rows("products"):
            if not r.chance(0.52):
                continue
            cid = p["customer_id"]
            if cid is None:
                continue
            aid = self.nid("part_approvals")
            req = self._spread_date(r, before_start_ok=True)
            sub = add_days(req, r.randint(15, 90))
            status = r.weighted(["Onaylandı", "Onaylandı", "Şartlı Onay", "Revizyon Talep Edildi",
                                 "Değerlendirmede", "Reddedildi"], [58, 16, 10, 7, 6, 3])
            appr = None
            if status in ("Onaylandı", "Şartlı Onay"):
                appr = add_days(sub, r.randint(10, 120))
                if appr > today:
                    appr = today
            self.add("part_approvals", {
                "id": aid, "approval_no": f"PPAP-{req.year}-{aid:05d}",
                "product_id": p["id"], "customer_id": cid,
                "program_name": p["program_name"] or "Genel Üretim",
                "submission_level": r.weighted(levels, [8, 16, 58, 10, 8]),
                "sample_qty": r.choice([5, 10, 15, 30, 50, 100]),
                "request_date": min(req, today),
                "submission_date": min(sub, today),
                "approval_date": appr, "status": status,
                "engineer_id": r.choice(self.engineers),
                "drawing_revision": p["revision"],
                "reject_reason": (r.choice(["Ölçüm raporu eksik", "Kapasite analizi yetersiz",
                                            "Cpk değeri düşük", "Malzeme sertifikası uygun değil",
                                            "Ambalaj onayı alınamadı"])
                                  if status in ("Reddedildi", "Revizyon Talep Edildi") else None),
                "days_to_approve": ((appr - sub).days if appr else None),
                "notes": r.choice(["", "", "Müşteri denetimi ile birlikte tamamlandı.",
                                   "Ölçüm raporları CMM ile alındı.",
                                   "Seri üretim onayı ile birlikte fiyat anlaşması yenilendi."]),
            })

    # ================================================================== satış ==
    def gen_sales(self):
        """Ciroyu yazılmış yıllık eğriye oturtur. Yurt içi ve ihracat ayrı ayrı
        hedeflenir; aylık aşım bir sonraki aya devredilir ki yıllık toplam
        eğriden sapmasın."""
        r = self.rng.stream("sales")
        self._prepare_customer_parts(r)
        carry = {"dom": 0.0, "exp": 0.0}
        for yi, year, m in self.months():
            month_target = self.p.revenue_for_year(yi) * self.p.seasonality[m - 1] / 12.0
            exp_t = max(0.0, month_target * self.export_share - carry["exp"])
            dom_t = max(0.0, month_target * (1 - self.export_share) - carry["dom"])
            spent_e = spent_d = 0.0
            guard = 0
            while spent_d < dom_t and guard < 900:
                guard += 1
                spent_d += self._make_order(r, year, m, is_export=False)
            guard = 0
            while spent_e < exp_t and guard < 900:
                guard += 1
                spent_e += self._make_order(r, year, m, is_export=True)
            carry["dom"] = spent_d - dom_t
            carry["exp"] = spent_e - exp_t
        self._so_lines_by_order = {}
        for l in self.rows("sales_order_lines"):
            self._so_lines_by_order.setdefault(l["order_id"], []).append(l)
        self._classify_customers()

    def _classify_customers(self):
        """ABC sınıfı fiili ciroya göre atanır: cironun ilk %80'ini yapanlar A,
        sonraki %15 B, kalan C. Rastgele atanırsa en büyük müşteri C sınıfında
        görünür ve veri kendi içinde çelişir."""
        rev = {}
        for l in self.rows("sales_order_lines"):
            o = self._order_by_id_local(l["order_id"])
            if o["status"] == SO_CANCEL:
                continue
            rev[o["customer_id"]] = rev.get(o["customer_id"], 0.0) + l["line_subtotal_base"]
        total = sum(rev.values()) or 1.0
        cum = 0.0
        for cid, v in sorted(rev.items(), key=lambda kv: -kv[1]):
            cum += v
            share = cum / total
            self._cust[cid]["abc_class"] = "A" if share <= 0.80 else (
                "B" if share <= 0.95 else "C")
        for c in self.rows("customers"):
            if c["id"] not in rev:
                c["abc_class"] = "C"

    def _order_by_id_local(self, oid):
        if not hasattr(self, "_o_idx"):
            self._o_idx = {o["id"]: o for o in self.rows("sales_orders")}
        return self._o_idx[oid]

    def _prepare_customer_parts(self, r):
        """Her müşteriye en az bir parça numarası düşsün; bir fason imalatçıda
        parçalar müşteriye özeldir, ortak katalog yoktur."""
        self._cust_products = {}
        for p in self.rows("products"):
            self._cust_products.setdefault(p["customer_id"], []).append(p["id"])
        spare = [p["id"] for p in self.rows("products")]
        for c in self.rows("customers"):
            if c["id"] not in self._cust_products:
                take = r.sample(spare, r.randint(1, 3))
                for pid in take:
                    self._prod[pid]["customer_id"] = c["id"]
                self._cust_products[c["id"]] = list(take)
        self._cust_picker_cache = {}
        for cid, pids in self._cust_products.items():
            self._cust_picker_cache[cid] = WeightedPicker(
                pids, [self._prod[p]["_popularity"] * r.lognormal(1.0, 0.6) for p in pids],
                self.rng.stream(f"cp{cid}"))

    def _make_order(self, r, year, month, is_export):
        picker = self._export_picker if is_export else self._domestic_picker
        if picker is None:
            picker = self._customer_picker
        cust = self._cust[picker.pick()]
        odate = self._clamp(random_date_in_month(r, year, month))
        ccy = cust["currency"]
        rate = self.fx(ccy, odate)
        try_eur = self.try_per("EUR", odate)
        p_drift = self._drift(odate, self.real_price_drift)
        c_drift = self._drift(odate, self.real_cost_drift)
        pool = self._cust_picker_cache.get(cust["id"])
        n_lines = max(1, min(8, r.poisson(float(self.t.get("lines_per_order_mean", 3.1)) - 1) + 1))

        oid = self.nid("sales_orders")
        tax_code, tax_rate = self._tax_for(cust)
        subtotal = discount = tax = total = cogs = 0.0
        total_qty = 0.0
        idx = []
        seen = set()
        requested = add_days(odate, r.randint(7, 45))
        for ln in range(1, n_lines + 1):
            pid = pool.pick() if pool else self._product_picker.pick()
            if pid in seen:
                continue
            seen.add(pid)
            p = self._prod[pid]
            qty = self._lot_qty(r, p)
            unit_try = round(p["_price_eur"] * p_drift * try_eur * r.jitter(1.0, 0.02), 4)
            cost_try = round(p["_direct_eur"] * c_drift * try_eur * r.jitter(1.0, 0.05), 4)
            unit_price = round(unit_try * rate, 4)
            unit_cost_c = round(cost_try * rate, 4)
            disc = r.weighted([0.0, 0.0, 0.02, 0.04, 0.06, 0.10], [46, 20, 14, 10, 7, 3])
            line_sub = money(qty * unit_price)
            line_disc = money(line_sub * disc)
            taxable = line_sub - line_disc
            line_tax = money(taxable * tax_rate)
            line_total = money(taxable + line_tax)
            line_cogs = money(qty * unit_cost_c)
            base_sub = money(taxable / rate)
            base_cogs = money(qty * cost_try)
            lid = self.nid("sales_order_lines")
            self.add("sales_order_lines", {
                "id": lid, "order_id": oid, "line_no": ln, "product_id": pid, "qty": qty,
                "unit_price": unit_price, "discount_pct": round(disc * 100, 2),
                "line_subtotal": line_sub, "tax": line_tax, "line_total": line_total,
                "unit_cost": unit_cost_c, "line_cogs": line_cogs,
                "line_margin": money(taxable - line_cogs),
                "machine_unit_id": None, "line_type": "Mamul", "description": p["name"],
                "fx_rate": self._fxr(rate), "line_subtotal_base": base_sub,
                "line_total_base": money(line_total / rate), "line_cogs_base": base_cogs,
                "line_margin_base": money(base_sub - base_cogs),
                "line_subtotal_eur": self.eur(base_sub, odate),
                "line_subtotal_usd": self.usd(base_sub, odate),
                "line_cogs_eur": self.eur(base_cogs, odate),
                "line_margin_eur": self.eur(base_sub - base_cogs, odate),
                "line_margin_usd": self.usd(base_sub - base_cogs, odate),
                "unit_price_eur": round(p["_price_eur"] * p_drift, 4),
                "requested_date": requested, "shipped_qty": qty,
            })
            idx.append((lid, pid, qty, unit_price, line_total, base_sub, base_cogs))
            subtotal += line_sub
            discount += line_disc
            tax += line_tax
            total += line_total
            cogs += line_cogs
            total_qty += qty
        if not idx:
            return 0.0

        recent = odate >= add_days(self._today(), -40)
        status = r.weighted([SO_DONE, SO_OPEN, SO_CANCEL],
                            [10, 87, 3] if recent else [95.5, 2, 2.5])
        sub_b = money(sum(x[5] for x in idx))
        cogs_b = money(sum(x[6] for x in idx))
        tax_b = money(tax / rate)
        tot_b = money(total / rate)
        delay = r.weighted([0, 0, 0, 1, 2, 3, 5, 9, 14], [52, 14, 8, 7, 6, 5, 4, 3, 1])
        shipped = self._clamp(add_days(requested, delay))
        terms = cust["payment_terms_days"]
        self.add("sales_orders", {
            "id": oid, "order_no": f"SIP-{odate.year}-{oid:06d}", "customer_id": cust["id"],
            "salesperson_id": cust["account_manager_id"],
            "warehouse_id": self._wh_fg,
            "channel": self._channel(r, cust), "order_date": odate, "status": status,
            "currency": ccy, "subtotal": money(subtotal), "discount": money(discount),
            "tax": money(tax), "total": money(total), "cogs": money(cogs),
            "margin": money(subtotal - discount - cogs),
            "quote_id": None, "opportunity_id": None,
            "order_type": "İhracat Siparişi" if cust["is_export"] else "Yurt İçi Sipariş",
            "fx_rate": self._fxr(rate), "subtotal_base": sub_b,
            "discount_base": money(discount / rate), "tax_base": tax_b, "total_base": tot_b,
            "cogs_base": cogs_b, "margin_base": money(sub_b - cogs_b),
            "incoterm": cust["incoterm"], "dest_country": cust["country_code"],
            "is_export": cust["is_export"], "is_intra_eu": cust["is_intra_eu"],
            "tax_code": tax_code, "payment_terms_days": terms,
            "delivery_date": shipped,
            "fx_rate_eur": round(self.try_per("EUR", odate), 6),
            "fx_rate_usd": round(self.try_per("USD", odate), 6),
            "subtotal_eur": self.eur(sub_b, odate), "subtotal_usd": self.usd(sub_b, odate),
            "total_eur": self.eur(tot_b, odate), "total_usd": self.usd(tot_b, odate),
            "cogs_eur": self.eur(cogs_b, odate),
            "margin_eur": self.eur(sub_b - cogs_b, odate),
            "margin_usd": self.usd(sub_b - cogs_b, odate),
            "customer_po_no": f"{cust['supplier_code']}-{r.randint(100000, 999999)}",
            "requested_date": requested, "confirmed_date": add_days(odate, r.randint(0, 3)),
            "shipped_date": shipped if status != SO_CANCEL else None,
            "is_on_time": delay <= 0, "delay_days": delay, "total_qty": round(total_qty, 2),
            "order_source": r.weighted(self.t.get("order_sources", ["E-posta Sipariş"]),
                                       [34, 26, 16, 10, 14][:len(self.t.get("order_sources", [1]))]),
            "notes": self._order_note(r, cust, delay),
        })
        if cust["first_order_date"] is None or odate < cust["first_order_date"]:
            cust["first_order_date"] = odate
        if status == SO_CANCEL:
            return 0.0
        self._make_invoice(r, oid, cust, odate, ccy, rate, sub_b, tax_b, idx, terms, recent)
        if status == SO_DONE and r.chance(self.p.return_rate):
            self._make_return(r, oid, cust, odate, ccy, rate, idx)
        return sub_b

    def _lot_qty(self, r, p):
        """Sipariş adedi. Seeds'teki lot_min/lot_max parçanın YILLIK adet
        bandıdır; OEM müşteriler yıllık sözleşmeyi haftalık/aylık çağrı planı
        (call-off) ile çeker, bu yüzden tek siparişe düşen miktar bölünür."""
        div = self._call_off_div
        lo, hi = p["_lot_min"] / div, p["_lot_max"] / div
        q = r.lognormal_mean((lo + hi) / 2.0, 0.55)
        q = max(lo * 0.35, min(hi * 2.2, q))
        step = 100 if q > 2000 else (50 if q > 500 else (10 if q > 100 else 5))
        return float(max(step, int(round(q / step)) * step))

    def _tax_for(self, cust):
        if cust["is_export"]:
            return "TR-IHR-0", 0.0
        return "TR-KDV-20", self.vat_rate

    def _channel(self, r, cust):
        if cust["is_export"]:
            return "İhracat"
        if cust["segment"] == "Kurumsal / OEM":
            return r.weighted(["OEM Sözleşmeli Üretim", "Tier-1 Fason Üretim",
                               "Yedek Parça / Aftermarket"], [62, 30, 8])
        return r.weighted(["Tier-1 Fason Üretim", "Doğrudan Satış",
                           "Yedek Parça / Aftermarket", "Proje / Numune"], [38, 40, 15, 7])

    @staticmethod
    def _order_note(r, cust, delay):
        if delay > 5:
            return r.choice([
                "Hammadde tedarikindeki gecikme nedeniyle termin ötelendi.",
                "Fason ısıl işlem dönüşü geciktiği için sevkiyat kaydı.",
                "Tezgah arızası nedeniyle üretim planı revize edildi.",
                "Müşteri onayı beklendiği için sevkiyat ertelendi."])
        return r.weighted(
            ["", "", "", "Kısmi sevkiyat yapılacaktır.",
             "Müşteri ambalaj talimatına göre KLT kasa ile sevk edilecek.",
             "Ölçüm raporu (COC) sevkiyat evrakına eklenecek.",
             "Yıllık fiyat anlaşması kapsamındadır.",
             "EDI çağrı planına göre haftalık sevkiyat.",
             "Acil sipariş - öncelikli üretim.",
             "Malzeme sertifikası (3.1) talep edilmiştir."],
            [40, 12, 8, 6, 7, 7, 6, 6, 4, 4])

    # =============================================================== fatura ==
    def _make_invoice(self, r, oid, cust, odate, ccy, rate, sub_b, tax_b, idx, terms, recent):
        iid = self.nid("invoices")
        idate = self._clamp(add_days(odate, r.choice([0, 0, 1, 2, 3, 5, 7])))
        due = add_days(idate, terms)
        today = self._today()
        subtotal = money(sub_b * rate)
        tax = money(tax_b * rate)
        total = money(subtotal + tax)
        dpd = (today - due).days

        if dpd <= 0:
            status, paid = (INV_OPEN, 0.0) if r.chance(0.86) else (INV_PAID, total)
        elif dpd <= 150:
            if r.chance(self.p.overdue_rate):
                status, paid = INV_LATE, (0.0 if r.chance(0.6)
                                          else money(total * r.rand() * 0.6))
            else:
                status, paid = INV_PAID, total
        elif dpd <= 450:
            status, paid = ((INV_LATE, 0.0) if r.chance(0.025) else (INV_PAID, total))
        else:
            status, paid = INV_PAID, total
        balance = money(total - paid)
        if balance <= 0:
            status, balance, paid = INV_PAID, 0.0, total

        self.add("invoices", {
            "id": iid, "invoice_no": f"FTR-{idate.year}-{iid:06d}", "order_id": oid,
            "customer_id": cust["id"], "invoice_date": idate, "due_date": due,
            "status": status, "currency": ccy, "subtotal": subtotal, "tax": tax,
            "total": total, "amount_paid": paid, "balance": balance,
            "fx_rate": self._fxr(rate),
            "subtotal_base": sub_b, "tax_base": tax_b, "total_base": money(sub_b + tax_b),
            "amount_paid_base": money(paid / rate), "balance_base": money(balance / rate),
            "tax_code": self._tax_for(cust)[0], "payment_terms_days": terms,
            "dest_country": cust["country_code"],
            "days_overdue": max(0, dpd) if balance > 0 else 0,
            "fx_rate_eur": round(self.try_per("EUR", idate), 6),
            "fx_rate_usd": round(self.try_per("USD", idate), 6),
            "subtotal_eur": self.eur(sub_b, idate), "subtotal_usd": self.usd(sub_b, idate),
            "total_eur": self.eur(sub_b + tax_b, idate),
            "total_usd": self.usd(sub_b + tax_b, idate),
            "balance_eur": self.eur(balance / rate, idate),
            "balance_usd": self.usd(balance / rate, idate),
            "e_invoice_no": f"GIB{idate.year}{iid:09d}",
            "invoice_type": ("İhracat Faturası (e-Arşiv)" if cust["is_export"]
                             else "Satış Faturası (e-Fatura)"),
        })
        ln = 0
        for (lid, pid, qty, up, lt, bsub, bcogs) in idx:
            ln += 1
            self.add("invoice_lines", {
                "id": self.nid("invoice_lines"), "invoice_id": iid, "line_no": ln,
                "product_id": pid, "qty": qty, "unit_price": up, "line_total": lt,
                "machine_unit_id": None, "line_type": "Mamul",
                "description": self._prod[pid]["name"],
                "line_total_base": money(lt / rate),
            })
        if paid > 0:
            pay_date = add_days(due, r.choice([-20, -8, -2, 0, 1, 4, 9, 17, 28])
                                if status != INV_LATE else r.choice([12, 25, 45, 75]))
            pay_date = max(idate, min(pay_date, today))
            prate = self.fx(ccy, pay_date)
            amount_base = money(paid / prate)
            self.add("payments", {
                "id": self.nid("payments"),
                "payment_no": f"THS-{self._ids['payments']:07d}", "invoice_id": iid,
                "customer_id": cust["id"], "payment_date": pay_date,
                "method": r.weighted(PAYMENT_METHODS,
                                     [34, 22, 8, 14, 12, 6, 4] if cust["is_export"]
                                     else [40, 26, 12, 2, 8, 8, 4]),
                "amount": paid, "currency": ccy, "fx_rate": self._fxr(prate),
                "amount_base": amount_base,
                "fx_gain_loss": money(amount_base - (paid / rate)),
                "days_to_pay": (pay_date - idate).days,
                "bank_account": f"{r.choice(BANK_NAMES)} - {ccy} Hesabı",
                "amount_eur": self.eur(amount_base, pay_date),
                "amount_usd": self.usd(amount_base, pay_date),
            })

    def _make_return(self, r, oid, cust, odate, ccy, rate, idx):
        lid, pid, qty, up, lt, bsub, bcogs = r.choice(idx)
        rqty = float(max(1, int(qty * r.weighted([0.02, 0.05, 0.1, 0.25, 1.0],
                                                 [34, 26, 22, 14, 4]))))
        refund = money(rqty * up)
        rid = self.nid("returns")
        self.add("returns", {
            "id": rid, "return_no": f"IAD-{rid:06d}", "order_id": oid, "order_line_id": lid,
            "product_id": pid, "customer_id": cust["id"],
            "return_date": self._clamp(add_days(odate, r.randint(10, 120))), "qty": rqty,
            "reason": r.choice([
                "Ölçü tolerans dışı", "Yüzey kalitesi uygun değil", "Çapak tespit edildi",
                "Yanlış revizyon sevk edildi", "Ambalaj hasarı", "Sertlik değeri düşük",
                "Kaplama hatası", "Fazla sevkiyat", "Müşteri programı iptal edildi",
                "İzlenebilirlik etiketi hatalı"]),
            "refund_amount": refund, "machine_unit_id": None, "currency": ccy,
            "refund_amount_base": money(refund / rate),
            "restocking_fee": 0.0,
            "status": r.weighted(["İade Alındı", "Alacak Dekontu Kesildi", "Reddedildi"],
                                 [56, 38, 6]),
            "ncr_id": None,
            "credit_note_no": f"ADK-{odate.year}-{rid:05d}",
        })

    # ================================================================= üretim ==
    def gen_production(self):
        """Talep, satış siparişi satırlarından aylık olarak toplanır; her ürün-ay
        için bir veya birkaç iş emri açılır ve rotadaki her operasyon tek tek
        işlenir. Fason adımlar ayrı bir tedarik akışı yaratır."""
        r = self.rng.stream("prod_ord")
        demand = {}
        so = {o["id"]: o for o in self.rows("sales_orders")}
        for l in self.rows("sales_order_lines"):
            o = so[l["order_id"]]
            if o["status"] == SO_CANCEL:
                continue
            key = (l["product_id"], o["order_date"].year, o["order_date"].month)
            d = demand.setdefault(key, [0.0, None])
            d[0] += float(l["qty"])
            if d[1] is None or o["order_date"] < d[1]:
                d[1] = o["order_date"]
            if len(d) < 6:
                d.append(o["id"])

        self._ops_by_wc = {}
        for e in self.rows("employees"):
            if e["is_active"] and e["work_center_id"]:
                self._ops_by_wc.setdefault(e["work_center_id"], []).append(e["id"])
        supervisors = self._emp_by_dept.get("Üretim", []) or self.operators
        today = self._today()
        shifts = self.t.get("shifts", ["1. Vardiya", "2. Vardiya", "3. Vardiya"])
        shift_w = self.t.get("shift_weights", [42, 34, 24])
        ovh_rate = float(self.t.get("shop_overhead_rate_pct", 0.16))

        for (pid, y, m), info in sorted(demand.items()):
            qty_needed, first_date = info[0], info[1]
            order_ids = info[2:]
            p = self._prod[pid]
            routing = self._routing_by_product.get(pid) or []
            if not routing:
                continue
            n_wo = 1 if qty_needed <= p["_lot_max"] else min(4, 1 + int(qty_needed // max(
                1, p["_lot_max"])))
            remaining = qty_needed * r.jitter(1.075, 0.02)
            for k in range(n_wo):
                planned = (remaining if k == n_wo - 1
                           else round(remaining / (n_wo - k) * r.jitter(1.0, 0.12), 0))
                planned = float(max(10.0, round(planned)))
                remaining = max(0.0, remaining - planned)
                self._one_work_order(r, p, routing, planned, y, m, first_date,
                                     order_ids, supervisors, shifts, shift_w, ovh_rate, today)

        self._wo_by_id = {w["id"]: w for w in self.rows("production_orders")}

    def _one_work_order(self, r, p, routing, planned_qty, y, m, first_date, order_ids,
                        supervisors, shifts, shift_w, ovh_rate, today):
        woid = self.nid("production_orders")
        start = random_date_in_month(r, y, m)
        lead = max(2, int(sum((rt["cycle_time_sec"] or 0) for rt in routing)
                          * planned_qty / 3600.0 / 16.0) + r.randint(1, 6))
        planned_start = self._clamp(add_days(start, -r.randint(0, 6)))
        planned_end = add_days(planned_start, lead)
        actual_start = self._clamp(add_days(planned_start, r.weighted([0, 1, 2, 4],
                                                                     [64, 20, 10, 6])))
        actual_end = add_days(actual_start, max(1, int(lead * r.jitter(1.05, 0.22))))
        if actual_end > today:
            if actual_start > today:
                status = WO_PLANNED
            else:
                status = WO_WIP
        else:
            status = WO_DONE if r.chance(0.996) else WO_CANCEL
        shift = r.weighted(shifts, shift_w)
        try_eur_s = self.try_per("EUR", actual_start)
        c_drift = self._drift(actual_start, self.real_cost_drift)

        # --- operasyonlar
        input_qty = planned_qty
        total_scrap = total_rework = 0.0
        labor_c = machine_c = tool_c = sub_c = 0.0
        setup_tot = run_tot = down_tot = 0.0
        op_rows = []
        for rt in routing:
            opid = self.nid("production_operations")
            op_date = self._clamp(add_days(actual_start, len(op_rows)
                                           * max(1, lead // max(1, len(routing)))))
            if rt["is_subcontract"]:
                scrap = round(input_qty * r.jitter(rt["scrap_pct"], 0.8) / 100.0, 2)
                good = max(0.0, round(input_qty - scrap, 2))
                cost = money((rt["subcontract_unit_price"] or 0) * c_drift
                             * self.try_per("EUR", op_date) * input_qty)
                sub_c += cost
                op_rows.append(self._add_operation(
                    r, opid, woid, rt, p, op_date, None, None, shift, input_qty, good,
                    scrap, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, cost, status, sub=True))
                total_scrap += scrap
                input_qty = good
                continue
            wc_pool = self._mach_by_wc.get(rt["work_center_id"], [])
            mach_id = rt["machine_id"] or (r.choice(wc_pool) if wc_pool else None)
            op_pool = self._ops_by_wc.get(rt["work_center_id"]) or self.operators
            operator = r.choice(op_pool)
            cyc = float(rt["cycle_time_sec"] or 10)
            setup_std = float(rt["setup_minutes"] or 0)
            run_std = round(input_qty * cyc / 60.0, 2)
            # Performans kaybı (takım aşınması, besleme düşürme, elle müdahale) ve
            # duruşlar OEE'yi belirler. Bunlar olmadan her iş merkezi %95+ OEE ile
            # çalışıyor gibi görünür; gerçek bir talaşlı imalat atölyesinde OEE
            # %65-80 bandındadır.
            eff = r.lognormal(float(self.t.get("performance_loss_factor", 1.12)), 0.17)
            run_act = round(run_std * eff, 2)
            setup_act = round(setup_std * r.jitter(1.12, 0.30), 2)
            down = round(max(0.0, r.lognormal(run_std * float(
                self.t.get("downtime_share", 0.155)), 0.9))
                if r.chance(float(self.t.get("downtime_chance", 0.66))) else 0.0, 2)
            scrap = round(input_qty * max(0.0, r.jitter(rt["scrap_pct"], 0.85)) / 100.0, 2)
            rework = round(input_qty * max(0.0, r.jitter(0.45, 0.9)) / 100.0
                           if r.chance(0.22) else 0.0, 2)
            good = max(0.0, round(input_qty - scrap, 2))
            hours = (setup_act + run_act + down) / 60.0
            lab = money(hours * rt["_labor_eur"] * rt["_operators_per_machine"]
                        * c_drift * self.try_per("EUR", op_date))
            mac = money(hours * rt["_machine_eur"] * c_drift * self.try_per("EUR", op_date))
            tol = money((rt["tooling_cost_per_part"] or 0) * c_drift
                        / self.try_per("EUR", self._today())
                        * self.try_per("EUR", op_date) * input_qty)
            labor_c += lab
            machine_c += mac
            tool_c += tol
            setup_tot += setup_act
            run_tot += run_act
            down_tot += down
            total_scrap += scrap
            total_rework += rework
            op_rows.append(self._add_operation(
                r, opid, woid, rt, p, op_date, mach_id, operator, shift, input_qty, good,
                scrap, rework, setup_std, setup_act, run_std, run_act, down,
                money(lab + mac + tol), status, lab=lab, mac=mac, tol=tol))
            input_qty = good

        produced = round(input_qty, 2)
        good_qty = produced
        # --- malzeme tüketimi
        mat_c = 0.0
        for (rm_id, qty_per) in p.get("_bom_lines", []):
            rm = self._rm[rm_id]
            planned_c = round(planned_qty * qty_per * 1.022, 4)
            consumed = round(planned_c * r.jitter(1.008, 0.02), 4)
            unit_cost = round(rm["_price_eur"] * c_drift * try_eur_s, 4)
            cost = money(consumed * unit_cost)
            mat_c += cost
            self.add("production_consumption", {
                "id": self.nid("production_consumption"), "production_order_id": woid,
                "raw_material_id": rm_id, "planned_qty": planned_c,
                "consumed_qty": consumed, "unit_cost": unit_cost,
                "issue_date": actual_start, "warehouse_id": self._wh_rm,
                "lot_no": f"HM{actual_start.year}{r.randint(10000, 99999)}",
                "total_cost": cost, "variance_qty": round(consumed - planned_c, 4),
            })

        overhead = money((mat_c + labor_c + machine_c + tool_c + sub_c) * ovh_rate)
        total_cost = money(mat_c + labor_c + machine_c + tool_c + sub_c + overhead)
        std_total = money(planned_qty * p["std_cost_total"] * c_drift
                          * try_eur_s / self.try_per("EUR", self._today()))
        lot_no = f"LOT-{actual_start.year}{actual_start.month:02d}-{woid:06d}"
        delay = max(0, (actual_end - planned_end).days)
        self.add("production_orders", {
            "id": woid, "mo_no": f"IE-{actual_start.year}-{woid:06d}", "product_id": p["id"],
            "bom_id": p.get("_bom_id"), "work_center_id": routing[0]["work_center_id"],
            "planned_qty": planned_qty,
            "produced_qty": produced if status in (WO_DONE, WO_WIP) else 0.0,
            "scrap_qty": round(total_scrap, 2),
            "start_date": actual_start, "end_date": (actual_end if status == WO_DONE else None),
            "status": status,
            "unit_cost": round(total_cost / max(produced, 1.0), 4),
            "wo_no": f"IE-{actual_start.year}-{woid:06d}",
            "sales_order_id": (order_ids[0] if order_ids else None),
            "customer_id": p["customer_id"], "routing_version": p["revision"],
            "priority": r.weighted(["Normal", "Normal", "Yüksek", "Acil", "Düşük"],
                                   [52, 20, 16, 7, 5]),
            "lot_no": lot_no, "warehouse_id": self._wh_fg,
            "planner_id": r.choice(self.planners),
            "supervisor_id": r.choice(supervisors), "shift": shift,
            "planned_start": planned_start, "planned_end": planned_end,
            "actual_start": actual_start,
            "actual_end": (actual_end if status == WO_DONE else None),
            "good_qty": good_qty if status == WO_DONE else 0.0,
            "rework_qty": round(total_rework, 2),
            "yield_pct": round(100.0 * produced / planned_qty, 3) if planned_qty else None,
            "scrap_pct": round(100.0 * total_scrap / planned_qty, 3) if planned_qty else None,
            "material_cost": money(mat_c), "labor_cost": money(labor_c),
            "machine_cost": money(machine_c), "tooling_cost": money(tool_c),
            "subcontract_cost": money(sub_c), "overhead_cost": overhead,
            "total_cost": total_cost,
            "total_cost_eur": self.eur(total_cost, actual_start),
            "total_cost_usd": self.usd(total_cost, actual_start),
            "std_total_cost": std_total, "cost_variance": money(total_cost - std_total),
            "setup_minutes_total": round(setup_tot, 2), "run_minutes_total": round(run_tot, 2),
            "downtime_minutes_total": round(down_tot, 2),
            "is_on_time": delay <= 0, "delay_days": delay,
            "notes": self._wo_note(r, delay, total_scrap, planned_qty),
        })
        if status == WO_DONE:
            self.add("lots", {
                "id": self.nid("lots"), "lot_no": lot_no, "product_id": p["id"],
                "production_order_id": woid, "production_date": actual_end,
                "expiry_date": None, "qty": good_qty, "customer_id": p["customer_id"],
                "heat_no": f"DK{r.randint(100000, 999999)}",
                "material_lot": f"HM{actual_start.year}{r.randint(10000, 99999)}",
                "warehouse_id": self._wh_fg, "status": "Sevk Edildi",
                "remaining_qty": 0.0,
                "certificate_no": f"COC-{actual_end.year}-{woid:06d}",
            })

    def _add_operation(self, r, opid, woid, rt, p, op_date, mach_id, operator, shift,
                       input_qty, good, scrap, rework, setup_std, setup_act, run_std,
                       run_act, down, total_cost, wo_status, lab=0.0, mac=0.0, tol=0.0,
                       sub=False):
        hour = {"1. Vardiya": 8, "2. Vardiya": 16, "3. Vardiya": 0}.get(shift, 8)
        start_ts = datetime(op_date.year, op_date.month, op_date.day, hour,
                            r.randint(0, 55))
        end_ts = start_ts + timedelta(minutes=float(setup_act + run_act + down))
        row = {
            "id": opid, "production_order_id": woid, "routing_id": rt["id"],
            "operation_no": rt["operation_no"], "operation_name": rt["operation_name"],
            "operation_type": rt["operation_type"], "work_center_id": rt["work_center_id"],
            "machine_id": mach_id, "operator_id": operator, "shift": shift,
            "op_date": op_date, "start_ts": start_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "end_ts": end_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "setup_minutes_std": setup_std, "setup_minutes_actual": setup_act,
            "run_minutes_std": run_std, "run_minutes_actual": run_act,
            "downtime_minutes": down,
            "downtime_reason": (r.choice(DOWNTIME_REASONS) if down > 0 else None),
            "input_qty": input_qty, "good_qty": good, "scrap_qty": scrap,
            "rework_qty": rework, "labor_cost": money(lab), "machine_cost": money(mac),
            "tooling_cost": money(tol), "total_cost": money(total_cost),
            "efficiency_pct": (round(100.0 * run_std / run_act, 2)
                               if run_act > 0 else None),
            "status": ("Tamamlandı" if wo_status == WO_DONE else
                       ("Devam Ediyor" if wo_status == WO_WIP else wo_status)),
            "notes": ("Fason operasyon - tedarikçiye gönderildi" if sub else
                      (r.choice(["", "", "", "Takım değişimi yapıldı.",
                                 "İlk parça onayı alındı.", "Ölçü kontrolü yapıldı.",
                                 "Program optimizasyonu ile çevrim süresi düşürüldü."])
                       if r.chance(0.35) else "")),
        }
        self.add("production_operations", row)
        return row

    @staticmethod
    def _wo_note(r, delay, scrap, planned):
        if planned and scrap / planned > 0.05:
            return r.choice([
                "Yüksek hurda oranı - kök neden analizi başlatıldı.",
                "Takım aşınması nedeniyle hurda arttı, takım ömrü revize edildi.",
                "Hammadde partisinde sertlik sapması tespit edildi."])
        if delay > 3:
            return r.choice([
                "Fason dönüşü geciktiği için iş emri kapanışı ötelendi.",
                "Tezgah arızası nedeniyle üretim durdu.",
                "Öncelikli acil sipariş nedeniyle plan kaydırıldı."])
        return r.weighted(
            ["", "", "", "Planlandığı gibi tamamlandı.",
             "İlk parça onayı sonrası seri üretime geçildi.",
             "Vardiya devri ile iki vardiyada tamamlandı.",
             "Müşteri ambalaj talimatına göre paketlendi."], [46, 14, 10, 12, 8, 6, 4])

    # ================================================================== fason ==
    def gen_subcontract(self):
        """Isıl işlem, kaplama gibi dışarıda yaptırılan operasyonların sevk /
        dönüş takibi. Satınalma siparişleri gen_purchasing içinde bağlanır."""
        r = self.rng.stream("fason")
        rt_by_id = {rt["id"]: rt for rt in self.rows("routings")}
        wo = {w["id"]: w for w in self.rows("production_orders")}
        today = self._today()
        for op in self.rows("production_operations"):
            rt = rt_by_id.get(op["routing_id"])
            if not rt or not rt["is_subcontract"]:
                continue
            w = wo[op["production_order_id"]]
            vid = rt["subcontract_vendor_id"] or r.choice(list(self._vend))
            vend = self._vend[vid]
            sent = op["op_date"]
            planned_lead = int(vend["lead_time_days"] or 7)
            lead = max(1, int(planned_lead * r.jitter(1.12, 0.35)))
            recv = add_days(sent, lead)
            done = recv <= today and w["status"] in (WO_DONE,)
            ccy = rt["subcontract_currency"] or self.base_ccy
            unit_price_eur = float(rt["subcontract_unit_price"] or 0)
            rate = self.fx(ccy, sent)
            unit_price = round(unit_price_eur * (1.0 if ccy == "EUR" else 1.0), 5)
            total_base = money(op["total_cost"])
            sid = self.nid("subcontract_operations")
            self.add("subcontract_operations", {
                "id": sid, "sub_no": f"FSN-{sent.year}-{sid:06d}",
                "production_order_id": w["id"], "operation_id": op["id"], "vendor_id": vid,
                "purchase_order_id": None,
                "process_type": rt["_sub_process"] or rt["operation_name"],
                "sent_date": sent, "expected_date": add_days(sent, planned_lead),
                "received_date": (recv if done else None),
                "qty_sent": op["input_qty"],
                "qty_received": (op["good_qty"] if done else None),
                "qty_scrapped": (op["scrap_qty"] if done else None),
                "unit_price": unit_price, "currency": ccy, "fx_rate": self._fxr(rate),
                "total_cost": money(total_base * rate), "total_cost_base": total_base,
                "lead_days": (lead if done else None), "planned_lead_days": planned_lead,
                "is_on_time": (lead <= planned_lead if done else None),
                "status": ("Dönüş Yapıldı" if done else
                           ("Tedarikçide" if sent <= today else "Planlandı")),
                "notes": r.weighted(
                    ["", "", "", "Sertlik raporu ile birlikte teslim alındı.",
                     "Kaplama kalınlığı ölçümü yapıldı.",
                     "Kısmi dönüş - bakiye takipte.",
                     "Fason firmada kapasite darlığı nedeniyle gecikme."],
                    [50, 14, 10, 10, 8, 5, 3]),
            })
        self._sub_ops = self.rows("subcontract_operations")

    # ================================================================= kalite ==
    def gen_quality(self):
        r = self.rng.stream("kalite")
        today = self._today()
        q = self.t.get("quality", {})
        inspectors = self.quality_staff
        rt_by_id = {rt["id"]: rt for rt in self.rows("routings")}
        wos = [w for w in self.rows("production_orders") if w["status"] != WO_CANCEL]

        # --- final ve proses kontrolleri
        ops_by_wo = {}
        for op in self.rows("production_operations"):
            ops_by_wo.setdefault(op["production_order_id"], []).append(op)
        for w in wos:
            p = self._prod[w["product_id"]]
            ops = ops_by_wo.get(w["id"], [])
            checks = [("Final Kontrol", 1.0)]
            if r.chance(0.42):
                checks.append(("Proses Ara Kontrol", 0.6))
            if r.chance(0.30):
                checks.append(("İlk Parça Onayı (İPO)", 0.2))
            if p["is_safety_part"] and r.chance(0.55):
                checks.append(("Sevkiyat Öncesi Kontrol", 0.9))
            for itype, _w in checks:
                self._add_inspection(r, itype, w, p, ops, inspectors, today)

        # --- girdi kalite kontrolü (hammadde / fason dönüşü)
        for sub in self.rows("subcontract_operations"):
            if sub["received_date"] and r.chance(0.5):
                self._add_incoming_inspection(r, sub, inspectors, today)

        self._gen_ncrs(r, wos, ops_by_wo, today, q)

    def _add_inspection(self, r, itype, w, p, ops, inspectors, today):
        iid = self.nid("quality_inspections")
        d = w["actual_end"] or w["actual_start"]
        d = self._clamp(d)
        op = r.choice(ops) if ops else None
        char, unit = r.choice(QUALITY_CHARACTERISTICS)
        nominal = round(r.lognormal(24.0, 0.8), 3)
        tol = round(max(0.01, nominal * r.choice([0.001, 0.002, 0.004, 0.008])), 4)
        measured = round(nominal + r.lognormal(1.0, 0.0) * 0 +
                         (r.rand() - 0.5) * tol * 1.7, 4)
        sample = float(r.choice([3, 5, 8, 10, 15, 20, 32]))
        inspected = min(float(w["produced_qty"] or w["planned_qty"]),
                        sample * r.choice([1, 1, 2, 4]))
        base_rate = 0.004 if itype == "Final Kontrol" else 0.009
        defect = float(int(inspected * max(0.0, r.jitter(base_rate, 1.2))
                           if r.chance(0.22) else 0))
        ok = defect == 0 and abs(measured - nominal) <= tol
        cpk = round(max(0.55, r.lognormal(1.52, 0.24)), 3)
        self.add("quality_inspections", {
            "id": iid, "inspection_no": f"KK-{d.year}-{iid:07d}", "inspection_type": itype,
            "inspection_date": d, "production_order_id": w["id"],
            "operation_id": (op["id"] if op else None), "product_id": p["id"],
            "raw_material_id": None, "purchase_order_id": None, "vendor_id": None,
            "customer_id": p["customer_id"], "inspector_id": r.choice(inspectors),
            "work_center_id": (op["work_center_id"] if op else w["work_center_id"]),
            "lot_no": w["lot_no"], "sample_size": sample, "inspected_qty": inspected,
            "defect_qty": defect,
            "defect_ppm": round(1e6 * defect / inspected, 2) if inspected else 0,
            "result": ("Uygun" if ok else ("Şartlı Uygun" if r.chance(0.45) else "Uygunsuz")),
            "characteristic": f"{char} ({unit})",
            "measurement_method": r.choice(MEASUREMENT_METHODS),
            "nominal_value": nominal, "tolerance_lower": round(nominal - tol, 4),
            "tolerance_upper": round(nominal + tol, 4), "measured_value": measured,
            "cpk": cpk,
            "notes": r.weighted(["", "", "", "Ölçüm CMM ile doğrulandı.",
                                 "SPC kartına işlendi.", "Takım değişimi önerildi.",
                                 "Cpk hedefin altında, proses gözden geçirilecek."],
                                [52, 14, 10, 9, 7, 5, 3]),
        })

    def _add_incoming_inspection(self, r, sub, inspectors, today):
        iid = self.nid("quality_inspections")
        d = self._clamp(sub["received_date"])
        char, unit = r.choice([("Sertlik", "HRC"), ("Kaplama kalınlığı", "µm"),
                               ("Yüzey pürüzlülüğü Ra", "µm"), ("Dış çap", "mm")])
        nominal = round(r.lognormal(38.0, 0.5), 3)
        tol = round(nominal * 0.06, 4)
        measured = round(nominal + (r.rand() - 0.5) * tol * 1.9, 4)
        inspected = float(sub["qty_received"] or 0)
        defect = float(int(inspected * 0.004)) if r.chance(0.16) else 0.0
        self.add("quality_inspections", {
            "id": iid, "inspection_no": f"KK-{d.year}-{iid:07d}",
            "inspection_type": "Girdi Kontrol", "inspection_date": d,
            "production_order_id": sub["production_order_id"],
            "operation_id": sub["operation_id"], "product_id": None,
            "raw_material_id": None, "purchase_order_id": None,
            "vendor_id": sub["vendor_id"], "customer_id": None,
            "inspector_id": r.choice(inspectors), "work_center_id": None,
            "lot_no": None, "sample_size": float(r.choice([3, 5, 8, 10])),
            "inspected_qty": inspected, "defect_qty": defect,
            "defect_ppm": round(1e6 * defect / inspected, 2) if inspected else 0,
            "result": "Uygun" if defect == 0 else "Uygunsuz",
            "characteristic": f"{char} ({unit})",
            "measurement_method": r.choice(["Sertlik Ölçüm (HRC)", "Kaplama Kalınlık Ölçer",
                                            "Mikrometre", "Yüzey Pürüzlülük Cihazı"]),
            "nominal_value": nominal, "tolerance_lower": round(nominal - tol, 4),
            "tolerance_upper": round(nominal + tol, 4), "measured_value": measured,
            "cpk": None,
            "notes": "Fason dönüş girdi kontrolü",
        })

    def _gen_ncrs(self, r, wos, ops_by_wo, today, q):
        """Uygunsuzluk kayıtları: iç hurda/rework, tedarikçi kaynaklı ve müşteri
        şikayeti. 8D açılanlar müşteri şikayetlerinin çoğunu oluşturur."""
        internal_rate = float(q.get("internal_ncr_rate", 0.055))
        for w in wos:
            if not r.chance(internal_rate):
                continue
            ops = ops_by_wo.get(w["id"], [])
            op = r.choice(ops) if ops else None
            self._add_ncr(r, "İç Uygunsuzluk", w, op, None, None, today)
        vend_pool = [v for v in self.rows("vendors")
                     if v["vendor_type"] in ("Çelik Servis Merkezi", "Isıl İşlem (Fason)",
                                             "Yüzey Kaplama (Fason)", "Dövme Taslak",
                                             "Döküm Taslak", "Çubuk Çelik Tedarikçisi")]
        n_sup = max(30, int(len(wos) * float(q.get("supplier_ncr_rate", 0.022))))
        for _ in range(n_sup):
            w = r.choice(wos)
            self._add_ncr(r, "Tedarikçi Uygunsuzluğu", w, None,
                          r.choice(vend_pool)["id"] if vend_pool else None, None, today)
        n_cust = max(25, int(len(wos) * float(q.get("customer_complaint_rate", 0.012))))
        for _ in range(n_cust):
            w = r.choice(wos)
            self._add_ncr(r, "Müşteri Şikayeti", w, None, None,
                          self._prod[w["product_id"]]["customer_id"], today)

    def _add_ncr(self, r, source, w, op, vendor_id, customer_id, today):
        nid = self.nid("nonconformances")
        base_d = w["actual_end"] or w["actual_start"]
        d = self._clamp(add_days(base_d, r.randint(0, 40)))
        code, desc, cause = r.choice(DEFECT_CODES)
        p = self._prod[w["product_id"]]
        qty = float(max(1, int((w["produced_qty"] or w["planned_qty"])
                               * r.lognormal(0.028, 1.0))))
        unit_cost = p["unit_cost"] * self._drift(d, self.real_cost_drift) \
            * self.try_per("EUR", d) / self.try_per("EUR", self._today())
        disposition = r.weighted(DISPOSITIONS, [34, 30, 14, 8, 9, 5])
        scrap_cost = money(qty * unit_cost) if disposition == "Hurda" else 0.0
        rework_cost = (money(qty * unit_cost * r.jitter(0.28, 0.4))
                       if disposition == "Yeniden İşleme (Rework)" else 0.0)
        other = money(qty * unit_cost * r.jitter(0.06, 0.7)) if r.chance(0.4) else 0.0
        is_complaint = source == "Müşteri Şikayeti"
        severity = r.weighted(["Düşük", "Orta", "Yüksek", "Kritik"],
                              [30, 42, 22, 6] if is_complaint else [46, 38, 13, 3])
        is_8d = bool(is_complaint and r.chance(0.72)) or severity == "Kritik"
        closed = None
        capa = r.weighted(["Kapatıldı", "Kapatıldı", "Doğrulama Aşamasında", "Açık"],
                          [58, 20, 14, 8])
        if capa == "Kapatıldı":
            closed = self._clamp(add_days(d, r.randint(3, 95)))
        self.add("nonconformances", {
            "id": nid, "ncr_no": f"UYG-{d.year}-{nid:05d}", "source": source, "ncr_date": d,
            "product_id": p["id"], "production_order_id": w["id"],
            "operation_id": (op["id"] if op else None), "customer_id": customer_id,
            "vendor_id": vendor_id,
            "work_center_id": (op["work_center_id"] if op else w["work_center_id"]),
            "machine_id": (op["machine_id"] if op else None),
            "detected_by_id": r.choice(self.quality_staff), "qty_affected": qty,
            "defect_code": code, "defect_description": desc, "root_cause": cause,
            "root_cause_category": r.choice(ROOT_CAUSE_CATEGORIES),
            "disposition": disposition, "rework_cost": rework_cost, "scrap_cost": scrap_cost,
            "other_cost": other, "total_cost": money(rework_cost + scrap_cost + other),
            "is_customer_complaint": is_complaint,
            "complaint_ref": (f"MS-{d.year}-{nid:05d}" if is_complaint else None),
            "ppm": round(1e6 * qty / max(1.0, w["planned_qty"]), 2),
            "severity": severity, "capa_status": capa,
            "capa_owner_id": r.choice(self.engineers + self.quality_staff),
            "opened_date": d, "closed_date": closed,
            "days_to_close": ((closed - d).days if closed else None), "is_8d": is_8d,
            "notes": r.choice([
                "5 Neden analizi yapıldı, kök neden takım aşınması olarak belirlendi.",
                "Kontrol planı ve FMEA güncellendi.",
                "Operatör eğitimi tekrarlandı.",
                "Tedarikçiye 8D raporu gönderildi.",
                "Müşteriye sınıflandırma (sorting) desteği verildi.",
                "Poka-yoke aparatı tasarlandı ve devreye alındı.",
                "Ölçüm sıklığı artırıldı, SPC takibine alındı.",
                "Sapma onayı ile sevkiyata izin verildi."]),
        })

    # ================================================================== bakım ==
    def gen_maintenance(self):
        r = self.rng.stream("bakim")
        today = self._today()
        cfg = self.t.get("maintenance", {})
        prev = float(cfg.get("preventive_per_machine_per_year", 5.4))
        brk = float(cfg.get("breakdown_per_machine_per_year", 3.1))
        years = self.p.years - 1 + self.end_month / 12.0
        techs = self._emp_by_dept.get("Bakım ve Onarım", []) or self.technicians
        try_now = self.try_per("EUR", today)
        for mch in self.rows("machines"):
            n = int(round((prev + brk) * years * r.jitter(1.0, 0.3)))
            for _ in range(max(1, n)):
                is_planned = r.chance(prev / (prev + brk))
                mid = self.nid("maintenance_orders")
                req = self._clamp(random_date_in_month(
                    r, r.randint(self.p.start_year, self.p.end_year()), r.randint(1, 12)))
                if req < self.start_date:
                    req = self.start_date
                start = self._clamp(add_days(req, 0 if not is_planned else r.randint(0, 5)))
                downtime = round(r.lognormal(3.2 if is_planned else 7.5, 0.8), 2)
                end = self._clamp(add_days(start, 0 if downtime < 10 else r.randint(1, 4)))
                c_drift = self._drift(start, self.real_cost_drift)
                try_eur = self.try_per("EUR", start)
                labor_h = round(downtime * r.jitter(1.15, 0.3), 2)
                labor = money(labor_h * 9.5 * c_drift * try_eur)
                parts = money((r.lognormal(180, 1.15) if not is_planned
                               else r.lognormal(55, 0.8)) * c_drift * try_eur)
                ext = money(r.lognormal(420, 0.9) * c_drift * try_eur) \
                    if r.chance(0.16 if is_planned else 0.28) else 0.0
                self.add("maintenance_orders", {
                    "id": mid, "mo_no": f"BKM-{start.year}-{mid:06d}",
                    "machine_id": mch["id"], "work_center_id": mch["work_center_id"],
                    "maintenance_type": ("Planlı Periyodik Bakım" if is_planned
                                         else r.weighted(["Arıza Bakım", "Kestirimci Bakım",
                                                          "Kalibrasyon", "Revizyon / Overhol"],
                                                         [72, 12, 10, 6])),
                    "request_date": req, "start_date": start,
                    "end_date": end if end <= today else None,
                    "technician_id": r.choice(techs),
                    "downtime_hours": downtime, "labor_hours": labor_h,
                    "labor_cost": labor, "parts_cost": parts, "external_cost": ext,
                    "total_cost": money(labor + parts + ext),
                    "failure_mode": (None if is_planned else r.choice(FAILURE_MODES)),
                    "root_cause": (None if is_planned else r.choice([
                        "Yağlama yetersizliği", "Rulman ömrü doldu", "Aşırı yükleme",
                        "Talaş ve kir birikmesi", "Elektriksel dalgalanma",
                        "Periyodik bakım atlanmış", "Parça ömrü doldu",
                        "Operatör kullanım hatası"])),
                    "is_planned": is_planned,
                    "status": r.weighted(["Tamamlandı", "Tamamlandı", "Devam Ediyor", "Planlandı"],
                                         [88, 6, 4, 2]),
                    "notes": r.weighted(
                        ["", "", "Yağ ve filtre değişimi yapıldı.",
                         "Fener mili rulmanları değiştirildi.",
                         "Kızak yağlama sistemi temizlendi.",
                         "Üretici servisi çağrıldı.",
                         "Yedek parça temini beklendiği için gecikme oldu.",
                         "Geometrik hassasiyet ölçümü yapıldı ve kayıt altına alındı."],
                        [34, 12, 12, 8, 10, 8, 8, 8]),
                })

    # ==================================================================== İSG ==
    def gen_hse(self):
        r = self.rng.stream("isg")
        n_per_year = 26
        prod_depts = [d for d in self.rows("departments") if d["is_production"]] or \
            self.rows("departments")
        emps = [e for e in self.rows("employees") if e["is_active"]]
        for yi, year, m in self.months():
            if not r.chance(n_per_year / 12.0):
                continue
            for _ in range(max(1, r.poisson(n_per_year / 12.0))):
                iid = self.nid("hse_incidents")
                d = self._clamp(random_date_in_month(r, year, m))
                dept = r.choice(prod_depts) if r.chance(0.82) else r.choice(
                    self.rows("departments"))
                emp = r.choice(emps)
                itype = r.weighted(HSE_TYPES, [34, 20, 14, 8, 10, 3, 6, 5])
                lost = (r.randint(1, 21) if itype == "Kayıp Günlü İş Kazası" else 0)
                self.add("hse_incidents", {
                    "id": iid, "incident_no": f"ISG-{year}-{iid:04d}", "incident_date": d,
                    "department_id": dept["id"],
                    "work_center_id": (r.choice(self._wc_internal)
                                       if self._wc_internal and dept["is_production"] else None),
                    "employee_id": emp["id"], "incident_type": itype,
                    "severity": r.weighted(["Düşük", "Orta", "Yüksek"], [58, 33, 9]),
                    "lost_days": lost,
                    "body_part": r.choice(HSE_BODY_PARTS),
                    "description": r.choice([
                        "Talaş temizliği sırasında el kesiği oluştu.",
                        "Parça taşırken bel ağrısı şikayeti bildirildi.",
                        "Talaş sıçraması sonucu göz tahrişi meydana geldi.",
                        "Forklift manevrası sırasında ramak kala olay yaşandı.",
                        "Soğutma sıvısı dökülmesi sonucu kayma riski oluştu.",
                        "Tezgah kapağı açıkken çalışma tespit edildi.",
                        "Yağ sızıntısı nedeniyle zeminde kayganlık oluştu.",
                        "Kesici takım kutusu taşınırken parmak sıkışması yaşandı.",
                        "Elektrik panosunda kısa devre kaynaklı duman görüldü."]),
                    "root_cause": r.choice([
                        "Kişisel koruyucu donanım kullanılmamış",
                        "Talimatlara uyulmaması", "Yetersiz aydınlatma",
                        "Ekipman bakım eksikliği", "Ergonomik olmayan çalışma pozisyonu",
                        "Düzen ve temizlik (5S) eksikliği", "Eğitim eksikliği",
                        "Aceleci çalışma"]),
                    "corrective_action": r.choice([
                        "KKD kullanımı konusunda eğitim tekrarlandı.",
                        "Talaş temizleme aparatı temin edildi.",
                        "Zemin kaymaz malzeme ile kaplandı.",
                        "Forklift trafik planı revize edildi.",
                        "Makine güvenlik kilidi devreye alındı.",
                        "Risk değerlendirmesi güncellendi.",
                        "Kaldırma aparatı temin edildi.",
                        "Uyarı levhaları yenilendi."]),
                    "reported_by_id": r.choice(emps)["id"],
                    "is_lost_time": lost > 0,
                    "status": r.weighted(["Kapatıldı", "Kapatıldı", "Aksiyon Devam Ediyor"],
                                         [72, 16, 12]),
                })

    # ============================================================== satınalma ==
    def gen_purchasing(self):
        r = self.rng.stream("satinalma")
        self._material_pos(r)
        self._subcontract_pos(r)
        self._tooling_pos(r)
        self._vendor_billing_tr(r)

    def _material_pos(self, r):
        """Hammadde alımı, fiilen tüketilen miktarlardan türetilir. Değer değil
        miktar üzerinden ikmal yapılmazsa stok bakiyesi eksiye düşer."""
        need = {}
        for c in self.rows("production_consumption"):
            key = (c["issue_date"].year, c["issue_date"].month, c["raw_material_id"])
            need[key] = need.get(key, 0.0) + float(c["consumed_qty"])
        cover = float(self.t.get("replenishment_cover", 1.09))
        buyers = self._emp_by_dept.get("Satınalma", []) or self.salespeople
        by_month = {}
        for (y, m, rm_id), qty in need.items():
            by_month.setdefault((y, m), {})[rm_id] = qty
        for (y, m), items in sorted(by_month.items()):
            by_vendor = {}
            for rm_id, qty in items.items():
                vid = self._rm[rm_id]["vendor_id"] or r.choice(list(self._vend))
                by_vendor.setdefault(vid, []).append((rm_id, qty))
            for vid, lines in sorted(by_vendor.items()):
                i = 0
                while i < len(lines):
                    chunk = lines[i:i + r.randint(2, 6)]
                    i += len(chunk)
                    self._write_po(r, vid, y, m, chunk, "raw_material", "Hammadde Alımı",
                                   cover, buyers)

    def _subcontract_pos(self, r):
        buyers = self._emp_by_dept.get("Satınalma", []) or self.salespeople
        by_key = {}
        for s in self.rows("subcontract_operations"):
            by_key.setdefault((s["sent_date"].year, s["sent_date"].month,
                               s["vendor_id"]), []).append(s)
        for (y, m, vid), subs in sorted(by_key.items()):
            poid = self.nid("purchase_orders")
            vend = self._vend[vid]
            odate = self._clamp(min(s["sent_date"] for s in subs))
            ccy = vend["currency"]
            rate = self.fx(ccy, odate)
            subtotal = sub_b = 0.0
            ln = 0
            for s in subs:
                ln += 1
                s["purchase_order_id"] = poid
                lt_b = s["total_cost_base"]
                self.add("purchase_order_lines", {
                    "id": self.nid("purchase_order_lines"), "po_id": poid, "line_no": ln,
                    "item_type": "Fason Hizmet", "item_id": s["production_order_id"],
                    "qty": s["qty_sent"],
                    "unit_cost": round(lt_b * rate / max(1.0, float(s["qty_sent"])), 4),
                    "line_total": money(lt_b * rate),
                    "received_qty": (s["qty_received"] or 0.0),
                    "machine_unit_id": None,
                    "description": f"{s['process_type']} - İş Emri {s['production_order_id']}",
                    "line_total_base": lt_b,
                })
                subtotal += money(lt_b * rate)
                sub_b += lt_b
            self._close_po(r, poid, vid, odate, ccy, rate, subtotal, sub_b, "Fason Hizmet Alımı",
                           buyers, "Fason İşçilik")

    def _tooling_pos(self, r):
        """Kesici takım, aparat ve sarf malzemesi alımı; üretimde tüketilen
        takım maliyetine göre aylık olarak sipariş edilir."""
        buyers = self._emp_by_dept.get("Satınalma", []) or self.salespeople
        pool = self._vpool("Kesici Takım", "Bağlama Aparatı ve Fikstür",
                           "Ölçü ve Kontrol Ekipmanı", "Soğutma Sıvısı ve Kimyasal")
        by_month = {}
        for w in self.rows("production_orders"):
            if w["status"] == WO_CANCEL:
                continue
            key = (w["actual_start"].year, w["actual_start"].month)
            by_month[key] = by_month.get(key, 0.0) + float(w["tooling_cost"])
        for (y, m), amt in sorted(by_month.items()):
            if amt <= 0:
                continue
            n_po = r.randint(2, 5)
            for k in range(n_po):
                poid = self.nid("purchase_orders")
                vid = r.choice(pool)
                vend = self._vend[vid]
                odate = self._clamp(random_date_in_month(r, y, m))
                ccy = vend["currency"]
                rate = self.fx(ccy, odate)
                part = amt * r.jitter(1.06 / n_po, 0.3)
                subtotal = sub_b = 0.0
                for ln in range(1, r.randint(2, 6) + 1):
                    lt_b = money(part / 3.5 * r.jitter(1.0, 0.5))
                    if lt_b <= 0:
                        continue
                    qty = float(r.choice([10, 20, 25, 50, 100, 200, 500]))
                    self.add("purchase_order_lines", {
                        "id": self.nid("purchase_order_lines"), "po_id": poid, "line_no": ln,
                        "item_type": "Kesici Takım / Sarf", "item_id": None, "qty": qty,
                        "unit_cost": round(lt_b * rate / qty, 4),
                        "line_total": money(lt_b * rate), "received_qty": qty,
                        "machine_unit_id": None,
                        "description": r.choice([
                            "Karbür kesici uç (CNMG/DNMG)", "Karbür parmak freze",
                            "HSS matkap ucu seti", "Vidalı takım tutucu",
                            "Diş açma kılavuzu", "Pens ve kovan seti",
                            "Kanal açma bıçağı", "Kaba ve finiş freze takımı",
                            "Soğutma sıvısı konsantresi", "Bağlama aparatı yedek parçası",
                            "Ölçüm mastarı", "Talaş konveyör bıçağı"]),
                        "line_total_base": lt_b,
                    })
                    subtotal += money(lt_b * rate)
                    sub_b += lt_b
                if sub_b <= 0:
                    continue
                self._close_po(r, poid, vid, odate, ccy, rate, subtotal, sub_b,
                               "Kesici Takım ve Sarf Malzeme", buyers, "Kesici Takım / Sarf")

    def _write_po(self, r, vid, y, m, chunk, item_type, po_type, cover, buyers):
        poid = self.nid("purchase_orders")
        vend = self._vend[vid]
        odate = self._clamp(random_date_in_month(r, y, m))
        ccy = vend["currency"]
        rate = self.fx(ccy, odate)
        c_drift = self._drift(odate, self.real_cost_drift)
        try_eur = self.try_per("EUR", odate)
        subtotal = sub_b = 0.0
        ln = 0
        for (rm_id, qty) in chunk:
            rm = self._rm[rm_id]
            ln += 1
            order_qty = round(max(float(rm["moq"] or 1) * 0.2, qty * r.jitter(cover, 0.14)), 2)
            unit_b = round(rm["_price_eur"] * c_drift * try_eur * r.jitter(1.0, 0.045), 4)
            lt_b = money(order_qty * unit_b)
            self.add("purchase_order_lines", {
                "id": self.nid("purchase_order_lines"), "po_id": poid, "line_no": ln,
                "item_type": item_type, "item_id": rm_id, "qty": order_qty,
                "unit_cost": round(unit_b * rate, 4), "line_total": money(lt_b * rate),
                "received_qty": (order_qty if r.chance(0.965)
                                 else round(order_qty * (0.55 + r.rand() * 0.44), 2)),
                "machine_unit_id": None,
                "description": f"{rm['name']} ({rm['material_grade'] or rm['category']})",
                "line_total_base": lt_b,
            })
            subtotal += money(lt_b * rate)
            sub_b += lt_b
        if sub_b <= 0:
            return
        self._close_po(r, poid, vid, odate, ccy, rate, subtotal, sub_b, po_type, buyers,
                       "Hammadde")

    def _close_po(self, r, poid, vid, odate, ccy, rate, subtotal, sub_b, po_type, buyers,
                  spend_category):
        vend = self._vend[vid]
        today = self._today()
        status = (PO_OPEN if odate > add_days(today, -20)
                  else r.weighted([PO_RECEIVED, PO_OPEN, PO_CANCEL], [95, 3, 2]))
        # yurt içi alımda %20 indirilecek KDV; ithalatta gümrükte ödenir
        trate = self.vat_rate if vend["country_code"] == self.home_cc else self.vat_rate
        tax = money(subtotal * trate)
        total = money(subtotal + tax)
        exp_d = add_days(odate, int(vend["lead_time_days"] or 10))
        self.add("purchase_orders", {
            "id": poid, "po_no": f"SAS-{odate.year}-{poid:06d}", "vendor_id": vid,
            "warehouse_id": self._wh_rm, "order_date": odate, "status": status,
            "currency": ccy, "subtotal": money(subtotal), "tax": tax, "total": total,
            "po_type": po_type, "fx_rate": self._fxr(rate), "subtotal_base": money(sub_b),
            "tax_base": money(tax / rate), "total_base": money(sub_b + tax / rate),
            "buyer_id": r.choice(buyers),
            "incoterm": r.choice(["EXW", "FCA", "DAP", "CPT", "CIF"]),
            "expected_date": exp_d,
            "received_date": (self._clamp(add_days(exp_d, r.randint(-2, 9)))
                              if status == PO_RECEIVED else None),
            "origin_country": vend["country_code"],
            "fx_rate_eur": round(self.try_per("EUR", odate), 6),
            "fx_rate_usd": round(self.try_per("USD", odate), 6),
            "total_eur": self.eur(sub_b + tax / rate, odate),
            "total_usd": self.usd(sub_b + tax / rate, odate),
            "spend_category": spend_category,
            "notes": r.weighted(["", "", "Malzeme sertifikası (3.1) ile birlikte istenmiştir.",
                                 "Kısmi sevkiyat kabul edilir.",
                                 "Acil ihtiyaç - hızlı teslim talebi.",
                                 "Yıllık çerçeve sözleşme kapsamındadır."],
                                [52, 14, 14, 8, 6, 6]),
        })

    def _vendor_billing_tr(self, r):
        today = self._today()
        for po in self.rows("purchase_orders"):
            if po["status"] == PO_CANCEL:
                continue
            vend = self._vend[po["vendor_id"]]
            bdate = self._clamp(add_days(po["order_date"], r.randint(0, 12)))
            terms = int(vend["payment_terms_days"] or 30)
            due = add_days(bdate, terms)
            vbid = self.nid("vendor_invoices")
            total = po["total"]
            if due <= today:
                paid = total if r.chance(0.965) else money(total * r.rand() * 0.7)
            else:
                paid = total if r.chance(0.28) else 0.0
            balance = money(total - paid)
            status = ("Ödendi" if balance <= 0 else
                      ("Vadesi Geçti" if due < today else "Açık"))
            self.add("vendor_invoices", {
                "id": vbid, "bill_no": f"AF-{bdate.year}-{vbid:06d}",
                "vendor_id": po["vendor_id"], "po_id": po["id"], "bill_date": bdate,
                "due_date": due, "spend_category": po["spend_category"],
                "currency": po["currency"], "fx_rate": po["fx_rate"],
                "subtotal": po["subtotal"], "tax": po["tax"], "total": total,
                "total_base": po["total_base"], "amount_paid": paid, "balance": balance,
                "status": status,
                "total_eur": po["total_eur"], "total_usd": po["total_usd"],
                "balance_base": money(balance * po["fx_rate"]),
            })
            if paid > 0:
                pdate = add_days(due, r.choice([-10, -4, 0, 3, 9, 21]))
                pdate = max(bdate, min(pdate, today))
                prate = self.fx(po["currency"], pdate)
                self.add("vendor_payments", {
                    "id": self.nid("vendor_payments"),
                    "payment_no": f"TOD-{self._ids['vendor_payments']:07d}",
                    "vendor_invoice_id": vbid, "vendor_id": po["vendor_id"],
                    "payment_date": pdate,
                    "method": r.weighted(VENDOR_PAY_METHODS, [40, 30, 12, 10, 8]),
                    "currency": po["currency"], "fx_rate": self._fxr(prate), "amount": paid,
                    "amount_base": money(paid / prate),
                })

    # ==================================================================== CRM ==
    def gen_crm(self):
        """Yeni parça (nomination) süreçleri. Tekrarlayan çağrı siparişleri fırsat
        yaratmaz; fırsatlar yeni parça devreye alma projeleridir."""
        r = self.rng.stream("crm")
        self._leads_by_customer = {}
        self._gen_leads_tr(r)
        orders = [o for o in self.rows("sales_orders") if o["status"] != SO_CANCEL]
        if not orders:
            return
        sample = [o for o in orders if r.chance(0.11)]
        for o in sample:
            self._won_opp(r, o)
        n_lost = int(len(sample) * float(self.t.get("lost_opportunity_ratio", 1.6)))
        for _ in range(n_lost):
            self._lost_opp(r)

    def _gen_leads_tr(self, r):
        n = int(self.t.get("leads_count", 900))
        cust_ids = [c["id"] for c in self.rows("customers")]
        pool = (locales.TR_LOCATIONS * 3 + [l for l in locales.EU_LOCATIONS if l[6]]
                + locales.NEAR_EXPORT_LOCATIONS)
        cats = self.t.get("customer_industries", ["Otomotiv Tier-1"])
        for _ in range(n):
            lid = self.nid("leads")
            city, region, country, iso2, phone_cc, cur, in_eu = locales.location(r, pool)
            created = self._clamp(self._spread_date(r, before_start_ok=False))
            status = r.weighted(["Müşteriye Dönüştü", "Nitelikli", "Görüşme Sürüyor",
                                 "Elendi", "Yeni"], [22, 19, 24, 27, 8])
            conv_cid = conv_date = lost = None
            if status == "Müşteriye Dönüştü":
                conv_cid = r.choice(cust_ids)
                conv_date = self._clamp(add_days(created, r.randint(20, 300)))
                self._leads_by_customer.setdefault(conv_cid, []).append(lid)
            elif status == "Elendi":
                lost = r.choice(["Bütçe yok", "Uygun olmayan parça tipi",
                                 "Adet çok düşük", "Mükerrer kayıt",
                                 "Başka tedarikçi ile çalışıyor", "Ödeme koşulları uymadı",
                                 "Kapasitemiz uygun değil"])
            if iso2 == "TR":
                cname = (f"{r.choice(locales.TR_CO_HEADS)} {r.choice(locales.TR_CO_TAILS)} "
                         f"{locales.tr_company_suffix(r)}")
                fn, ln = locales.person(r, "tr")
            else:
                cname = (f"{r.choice(locales.INTL_HEADS)} {r.choice(locales.INTL_TAILS)} "
                         + (locales.company_suffix(r, iso2) if in_eu
                            else locales.near_export_suffix(r, iso2)))
                fn, ln = locales.person(r, "de")
            self.add("leads", {
                "id": lid, "lead_no": f"ADY-{created.year}-{lid:05d}", "company_name": cname,
                "contact_name": f"{fn} {ln}",
                "email": f"{self._ascii(fn)}.{self._ascii(ln)}@ornek.com".lower(),
                "phone": locales.phone_for(r, phone_cc), "country": country, "city": city,
                "source": r.choice(LEAD_SOURCES_TR), "interest_category": r.choice(cats),
                "created_date": created, "status": status, "score": r.randint(15, 98),
                "owner_id": r.choice(self.salespeople), "converted_customer_id": conv_cid,
                "converted_date": conv_date, "lost_reason": lost,
            })

    def _won_opp(self, r, order):
        cust = self._cust[order["customer_id"]]
        oid = self.nid("opportunities")
        created = max(self.start_date, add_days(order["order_date"], -r.randint(45, 300)))
        lines = self._so_lines_by_order.get(order["id"], [])
        p = self._prod[lines[0]["product_id"]] if lines else None
        leads = self._leads_by_customer.get(cust["id"])
        self.add("opportunities", {
            "id": oid, "opp_no": f"FRS-{created.year}-{oid:05d}", "customer_id": cust["id"],
            "lead_id": (r.choice(leads) if leads and r.chance(0.3) else None),
            "owner_id": order["salesperson_id"],
            "title": f"{p['category'] if p else 'Parça'} devreye alma - {cust['name']}",
            "product_category": (p["category"] if p else "Talaşlı Parça"),
            "machine_category": (p["_family"] if p else None), "created_date": created,
            "expected_close_date": add_days(created, r.randint(45, 240)),
            "close_date": order["order_date"], "stage": "Kazanıldı",
            "probability_pct": 100, "currency": order["currency"],
            "amount": money(order["total"] * r.jitter(9.0, 0.6)),
            "fx_rate": order["fx_rate"],
            "amount_base": money(order["total_base"] * r.jitter(9.0, 0.6)),
            "status": "Kazanıldı", "win_loss_reason": r.choice(WIN_REASONS_TR),
            "competitor": (r.choice(COMPETITORS_TR) if r.chance(0.6) else None),
            "source": r.choice(LEAD_SOURCES_TR),
        })
        q = self._quote(r, oid, cust, order, lines, created, "Kabul Edildi")
        order["opportunity_id"] = oid
        order["quote_id"] = q
        self._activities(r, oid, cust["id"], order["salesperson_id"], created,
                         order["order_date"], won=True)

    def _lost_opp(self, r):
        cust = self._cust[self._customer_picker.pick()]
        oid = self.nid("opportunities")
        created = self._clamp(self._spread_date(r, before_start_ok=False))
        pid = (self._cust_picker_cache[cust["id"]].pick()
               if cust["id"] in self._cust_picker_cache else self._product_picker.pick())
        p = self._prod[pid]
        ccy = cust["currency"]
        rate = self.fx(ccy, created)
        annual = p["_price_eur"] * self.try_per("EUR", created) * r.lognormal(38000, 0.9)
        stage = r.weighted(["Kaybedildi", "Teklif Aşamasında", "Numune Aşaması",
                            "Görüşme / Pazarlık"], [64, 13, 12, 11])
        is_open = stage != "Kaybedildi"
        close = None if is_open else self._clamp(add_days(created, r.randint(30, 280)))
        owner = r.choice(self.salespeople)
        self.add("opportunities", {
            "id": oid, "opp_no": f"FRS-{created.year}-{oid:05d}", "customer_id": cust["id"],
            "lead_id": None, "owner_id": owner,
            "title": f"{p['category']} teklifi - {cust['name']}",
            "product_category": p["category"], "machine_category": p["_family"],
            "created_date": created,
            "expected_close_date": add_days(created, r.randint(45, 270)),
            "close_date": close, "stage": stage,
            "probability_pct": {"Teklif Aşamasında": 40, "Numune Aşaması": 60,
                                "Görüşme / Pazarlık": 75, "Kaybedildi": 0}[stage],
            "currency": ccy, "amount": money(annual * rate), "fx_rate": self._fxr(rate),
            "amount_base": money(annual), "status": "Açık" if is_open else "Kaybedildi",
            "win_loss_reason": (None if is_open else r.choice(LOSS_REASONS_TR)),
            "competitor": (r.choice(COMPETITORS_TR) if r.chance(0.68) else None),
            "source": r.choice(LEAD_SOURCES_TR),
        })
        if r.chance(0.8):
            self._quote(r, oid, cust, None, None, created,
                        "Süresi Doldu" if is_open else "Kaybedildi", p, annual, ccy, rate, owner)
        self._activities(r, oid, cust["id"], owner, created, close or self._today(), won=False)

    def _quote(self, r, opp_id, cust, order, lines, created, status, fb_product=None,
               amount_base=None, ccy=None, rate=None, owner=None):
        qid = self.nid("quotations")
        qdate = self._clamp(add_days(created, r.randint(3, 40)))
        if order is not None:
            ccy = order["currency"]
            store_rate = order["fx_rate"]
            sub, disc, tax = order["subtotal"], order["discount"], order["tax"]
            tot, tot_b = order["total"], order["total_base"]
            sp, incoterm, conv = order["salesperson_id"], order["incoterm"], order["id"]
            src = [(l["product_id"], l["description"], l["qty"], l["unit_price"],
                    l["discount_pct"], l["line_total"]) for l in lines]
        else:
            sub = money(amount_base * rate)
            disc = money(sub * r.choice([0.0, 0.02, 0.04, 0.07]))
            tax = money((sub - disc) * (0.0 if cust["is_export"] else self.vat_rate))
            tot = money(sub - disc + tax)
            tot_b = money(tot / rate)
            sp, incoterm, conv = owner, cust["incoterm"], None
            store_rate = self._fxr(rate)
            src = [(fb_product["id"], fb_product["name"], 1000,
                    money(amount_base * rate / 1000), 0, tot)]
        self.add("quotations", {
            "id": qid, "quote_no": f"TKL-{qdate.year}-{qid:05d}", "opportunity_id": opp_id,
            "customer_id": cust["id"], "salesperson_id": sp, "quote_date": qdate,
            "valid_until": add_days(qdate, r.choice([15, 30, 30, 45, 60, 90])),
            "currency": ccy, "fx_rate": store_rate, "subtotal": sub, "discount": disc,
            "tax": tax,
            "total": tot, "total_base": tot_b, "status": status, "converted_order_id": conv,
            "incoterm": incoterm, "lead_time_days": r.choice([10, 15, 21, 30, 45, 60, 90]),
        })
        ln = 0
        for (pid, desc, qty, up, dpct, lt) in src:
            ln += 1
            self.add("quotation_lines", {
                "id": self.nid("quotation_lines"), "quote_id": qid, "line_no": ln,
                "product_id": pid, "machine_unit_id": None, "description": desc,
                "qty": qty, "unit_price": up, "discount_pct": dpct, "line_total": lt,
            })
        return qid

    def _activities(self, r, opp_id, cust_id, emp_id, start, end, won):
        n = r.randint(3, 12) if won else r.randint(1, 8)
        span = max(1, (end - start).days)
        for _ in range(n):
            d = self._clamp(add_days(start, r.randint(0, span)))
            self.add("crm_activities", {
                "id": self.nid("crm_activities"), "activity_date": d,
                "activity_type": r.choice(ACTIVITY_TYPES_TR), "opportunity_id": opp_id,
                "lead_id": None, "customer_id": cust_id, "employee_id": emp_id,
                "subject": r.choice([
                    "Teknik resim ve tolerans değerlendirmesi",
                    "Fiyat teklifi gönderildi", "Numune üretim planı görüşüldü",
                    "Müşteri fabrika denetimi yapıldı", "Ambalaj ve lojistik görüşmesi",
                    "Yıllık adet tahmini paylaşıldı", "Termin ve kapasite teyidi",
                    "Ödeme koşulları görüşüldü", "PPAP dosyası talep edildi",
                    "Malzeme kalitesi alternatifleri sunuldu",
                    "Kur farkı ve fiyat revizyonu görüşmesi"]),
                "outcome": r.weighted(["Olumlu", "Nötr", "Takip Gerekli", "Olumsuz"],
                                      [36, 29, 27, 8]),
                "duration_min": r.choice([10, 15, 20, 30, 45, 60, 90, 120, 180]),
            })

    # ================================================================ lojistik ==
    def gen_logistics(self):
        r = self.rng.stream("lojistik")
        today = self._today()
        inv_by_order = {i["order_id"]: i for i in self.rows("invoices")}
        road = self._carriers_by_mode.get("Karayolu", [])
        sea = self._carriers_by_mode.get("Denizyolu", [])
        air = self._carriers_by_mode.get("Havayolu", [])
        for o in self.rows("sales_orders"):
            if o["status"] == SO_CANCEL:
                continue
            lines = self._so_lines_by_order.get(o["id"], [])
            if not lines:
                continue
            cust = self._cust[o["customer_id"]]
            cc = cust["country_code"]
            weight = 0.0
            for l in lines:
                weight += float(self._prod[l["product_id"]]["gross_weight_kg"]) * float(l["qty"])
            weight = round(max(1.0, weight), 2)
            if cc == self.home_cc:
                mode = "Karayolu"
            elif cust["is_intra_eu"] or cc in ("RS", "MK", "BA", "AL", "XK", "GE", "AZ",
                                               "IQ", "IR", "SY", "JO"):
                mode = "Havayolu" if (weight < 60 and r.chance(0.10)) else "Karayolu"
            else:
                mode = r.weighted(["Denizyolu", "Karayolu", "Havayolu"], [66, 24, 10])
            pool = {"Karayolu": road, "Denizyolu": sea, "Havayolu": air}.get(mode) or road
            carrier = r.choice(pool) if pool else None
            ship = self._clamp(o["shipped_date"] or o["delivery_date"] or o["order_date"])
            transit = self._transit(r, mode, cc)
            delivered = add_days(ship, transit)
            c_drift = self._drift(ship, self.real_cost_drift)
            try_eur = self.try_per("EUR", ship)
            freight = money(self._freight_eur(r, mode, weight, cc) * c_drift * try_eur)
            insurance = money(o["total_base"] * r.jitter(0.0018, 0.4))
            packing = money((0.9 + weight * 0.016) * r.jitter(1.0, 0.3) * c_drift * try_eur)
            handling = money(freight * r.jitter(0.07, 0.4))
            total_cost = money(freight + insurance + packing + handling)
            billed = 0.0 if o["incoterm"] in ("EXW", "FCA", "FOB") else money(
                total_cost * r.jitter(0.85, 0.2))
            sid = self.nid("shipments")
            inv = inv_by_order.get(o["id"])
            pallets = max(1, int(weight / 620) + (1 if weight % 620 > 60 else 0))
            self.add("shipments", {
                "id": sid, "shipment_no": f"SVK-{ship.year}-{sid:06d}", "order_id": o["id"],
                "invoice_id": (inv["id"] if inv else None), "customer_id": cust["id"],
                "carrier_id": carrier, "warehouse_id": self._wh_fg, "ship_date": ship,
                "eta_date": add_days(ship, transit),
                "delivery_date": (delivered if delivered <= today else None),
                "incoterm": o["incoterm"], "mode": mode,
                "origin_country": self.home_cc, "dest_country": cc,
                "dest_city": cust["city"], "is_export": cust["is_export"],
                "is_intra_eu": cust["is_intra_eu"], "gross_weight_kg": weight,
                "volume_m3": round(weight / r.jitter(430, 0.2), 3), "packages": pallets,
                "container_type": self._container(r, mode, weight),
                "freight_cost": freight, "insurance_cost": insurance,
                "packing_cost": packing, "handling_cost": handling,
                "total_logistics_cost": total_cost, "currency": self.base_ccy,
                "fx_rate": 1.0, "cost_base": total_cost, "billed_to_customer": billed,
                "status": ("Teslim Edildi" if delivered <= today
                           else r.weighted(["Yolda", "Yüklendi"], [72, 28])),
                "tracking_no": f"{r.choice(['ARK', 'MNG', 'HRK', 'DHL', 'MSC', 'TCS'])}"
                               f"{r.randint(100000000, 999999999)}",
                "transit_days": transit,
                "cost_eur": self.eur(total_cost, ship),
                "cost_usd": self.usd(total_cost, ship),
                "pallet_count": pallets,
                "packaging_type": r.weighted(["KLT Plastik Kasa", "Ahşap Palet + Karton Kutu",
                                              "Metal Kasa (Gitterbox)", "Big Bag",
                                              "Ahşap Sandık (ISPM-15)"],
                                             [34, 32, 16, 8, 10]),
                "border_gate": (r.choice(BORDER_GATES) if cust["is_export"] else None),
                "plate_no": (f"{r.randint(1, 81):02d} {chr(r.randint(65, 90))}"
                             f"{chr(r.randint(65, 90))} {r.randint(100, 999)}"),
            })
            for l in lines:
                p = self._prod[l["product_id"]]
                self.add("shipment_lines", {
                    "id": self.nid("shipment_lines"), "shipment_id": sid,
                    "order_line_id": l["id"], "product_id": l["product_id"],
                    "machine_unit_id": None, "description": l["description"],
                    "qty": l["qty"],
                    "weight_kg": round(float(p["gross_weight_kg"]) * float(l["qty"]), 2),
                    "hs_code": p["hs_code"], "country_of_origin": "TR",
                })
            if cust["is_export"]:
                self._customs_tr(r, sid, ship, o, cust, lines)

    @staticmethod
    def _transit(r, mode, cc):
        base = {"Karayolu": 2, "Denizyolu": 18, "Havayolu": 3}[mode]
        far = {"TR": 0, "IQ": 4, "IR": 6, "AZ": 7, "GE": 5, "EG": 8, "SA": 9, "AE": 10,
               "DE": 6, "IT": 5, "PL": 6, "RO": 4, "BG": 3, "CZ": 6, "FR": 7, "ES": 8,
               "NL": 7, "GB": 8, "UZ": 12, "KZ": 14}
        return max(1, int(base + far.get(cc, 5) + r.randint(-1, 4)))

    @staticmethod
    def _freight_eur(r, mode, weight, cc):
        far = {"TR": 1.0, "BG": 1.5, "RO": 1.7, "GR": 1.6, "IQ": 1.8, "IR": 2.0,
               "GE": 1.9, "AZ": 2.2, "DE": 2.4, "IT": 2.1, "PL": 2.5, "CZ": 2.4,
               "FR": 2.6, "ES": 2.8, "NL": 2.6, "GB": 3.0, "EG": 2.2, "SA": 2.6,
               "AE": 2.8, "UZ": 3.2, "KZ": 3.4}.get(cc, 2.3)
        if mode == "Havayolu":
            return (90 + weight * 3.4) * far * r.jitter(1.0, 0.28)
        if mode == "Denizyolu":
            return (620 + weight * 0.052) * far * r.jitter(1.0, 0.26)
        return (85 + weight * 0.098) * far * r.jitter(1.0, 0.24)

    @staticmethod
    def _container(r, mode, weight):
        if mode == "Denizyolu":
            return r.weighted(["20ft Konteyner", "40ft Konteyner", "40ft HC Konteyner",
                               "Groupage (LCL)"], [38, 28, 14, 20])
        if mode == "Havayolu":
            return "Hava Kargo Paleti"
        if weight > 12000:
            return "Tenteli TIR (Komple)"
        if weight > 2500:
            return r.weighted(["Tenteli TIR (Parsiyel)", "Kamyon (Komple)"], [58, 42])
        return r.weighted(["Kamyon (Parsiyel)", "Kamyonet", "Kargo"], [52, 30, 18])

    def _customs_tr(self, r, sid, ship, order, cust, lines):
        """İhracat gümrükleme. AB'ye yapılan sanayi ürünü ihracatı Gümrük Birliği
        kapsamında A.TR ile, STA'lı ülkeler EUR.1 ile, diğerleri menşe
        şehadetnamesi ile gider."""
        cc = cust["country_code"]
        if cust["is_intra_eu"]:
            doc = r.weighted(["A.TR Dolaşım Belgesi", "İhracat Beyannamesi (EX-A)"], [78, 22])
            duty = 0.0
        elif cc in ("RS", "MK", "BA", "AL", "XK", "GE", "MA", "TN", "EG", "JO"):
            doc = r.weighted(["EUR.1 Dolaşım Sertifikası", "Menşe Şehadetnamesi",
                              "İhracat Beyannamesi (EX-A)"], [56, 26, 18])
            duty = 0.0 if doc == "EUR.1 Dolaşım Sertifikası" else r.choice([0.0, 2.0, 3.5])
        else:
            doc = r.weighted(["Menşe Şehadetnamesi", "İhracat Beyannamesi (EX-A)",
                              "ATA Karnesi"], [58, 38, 4])
            duty = r.choice([0.0, 0.0, 2.5, 4.0, 5.0, 6.5])
        value_base = order["subtotal_base"]
        did = self.nid("customs_declarations")
        self.add("customs_declarations", {
            "id": did, "declaration_no": f"{ship.year}GB{r.randint(100000, 999999)}",
            "shipment_id": sid, "decl_date": add_days(ship, -r.randint(0, 3)),
            "direction": "İhracat", "customs_office": r.choice(CUSTOMS_OFFICES),
            "document_type": doc,
            "hs_code": self._prod[lines[0]["product_id"]]["hs_code"], "dest_country": cc,
            "currency": order["currency"], "fx_rate": order["fx_rate"],
            "customs_value": money(value_base / order["fx_rate"]),
            "customs_value_base": value_base, "duty_rate_pct": duty,
            "duty_amount": money(value_base * duty / 100.0), "vat_amount": 0.0,
            "broker_id": (r.choice(self._brokers) if self._brokers else None),
            "broker_fee": money(r.jitter(95, 0.4) * self.try_per("EUR", ship)
                                * self._drift(ship, self.real_cost_drift)),
            "status": r.weighted(["Kapandı", "Kapandı", "İşlemde", "Düzeltme Yapıldı"],
                                 [76, 15, 6, 3]),
        })

    # ================================================================== bordro ==
    # Ramazan / Kurban bayramı ikramiye ayları (fabrika uygulaması)
    BONUS_MONTHS = {2022: (4, 7), 2023: (4, 6), 2024: (4, 6), 2025: (3, 6),
                    2026: (3, 5), 2027: (2, 5)}

    def gen_payroll(self):
        """Aylık bordro. Maaşlar TL'dir ve TL bazında enflasyona paralel artar;
        EUR karşılığı görece yatay seyreder — Türkiye'de üretim yapmanın ana
        sebeplerinden biri de budur. SGK ve gelir vergisi kesintileri, vardiya
        primi, fazla mesai, yol-yemek yardımı ve kıdem karşılığı ayrı ayrı
        tutulur."""
        r = self.rng.stream("bordro")
        emps = self.rows("employees")
        today = self._today()
        try_now = self.try_per("EUR", today)
        real_wage = float(self.t.get("real_wage_drift", 0.015))
        meal_eur = float(self.t.get("meal_allowance_eur", 68))
        transport_eur = float(self.t.get("transport_allowance_eur", 42))

        for yi, year, m in self.months():
            mstart = date(year, m, 1)
            mend = date(year, m, days_in_month(year, m))
            fx_month = self.try_per("EUR", mend)
            wage_factor = (fx_month / try_now) * ((1 + real_wage) ** (year - self.p.end_year()))
            active = [e for e in emps if e["hire_date"] <= mend
                      and (e["termination_date"] is None or e["termination_date"] >= mstart)]
            if not active:
                continue
            rid = self.nid("payroll_runs")
            gross_t = ded_t = net_t = cost_t = ot_t = 0.0
            b1, b2 = self.BONUS_MONTHS.get(year, (4, 6))
            for e in active:
                base = money(e["annual_gross"] * wage_factor / 12.0)
                is_shift = e["shift"] != "Normal Mesai"
                ot_hours = round(max(0.0, r.lognormal(16.0, 0.75)), 1) if (
                    e["overtime_eligible"] and r.chance(0.72)) else 0.0
                ot = money(base / 225.0 * 1.5 * ot_hours)
                shift_prem = money(base * 0.10) if (is_shift and e["shift"] != "1. Vardiya") \
                    else 0.0
                bonus = money(base * r.jitter(0.55, 0.2)) if m in (b1, b2) else 0.0
                if m == 12 and r.chance(0.55):
                    bonus = money(bonus + base * r.jitter(0.45, 0.3))
                meal = money(meal_eur * fx_month * r.jitter(1.0, 0.05))
                transport = money(transport_eur * fx_month * r.jitter(1.0, 0.06))
                allow = money(meal + transport)
                gross = money(base + ot + shift_prem + bonus)
                sgk_emp = money(gross * 0.14)
                unemp_emp = money(gross * 0.01)
                tax = money(max(0.0, gross - sgk_emp - unemp_emp) * r.jitter(0.155, 0.18))
                stamp = money(gross * 0.00759)
                other_ded = money(stamp + (gross * 0.004 if e["union_member"] else 0.0))
                net = money(gross - sgk_emp - unemp_emp - tax - other_ded)
                sgk_er = money(gross * 0.2075)
                unemp_er = money(gross * 0.02)
                severance = money(gross * 0.0833)
                er_other = money(allow + severance + gross * 0.008)
                cost = money(gross + sgk_er + unemp_er + er_other)
                self.add("payroll_items", {
                    "id": self.nid("payroll_items"), "payroll_run_id": rid,
                    "employee_id": e["id"], "period_year": year, "period_month": m,
                    "period_date": mend, "country": self.home_cc, "base_salary": base,
                    "overtime_pay": ot, "bonus": bonus, "allowances": allow,
                    "gross_pay": gross, "employee_social": money(sgk_emp + unemp_emp),
                    "income_tax": tax, "other_deductions": other_ded, "net_pay": net,
                    "employer_social": money(sgk_er + unemp_er), "employer_other": er_other,
                    "employer_cost": cost, "currency": self.base_ccy, "fx_rate": 1.0,
                    "employer_cost_base": cost,
                    "employer_cost_eur": self.eur(cost, mend),
                    "employer_cost_usd": self.usd(cost, mend),
                    "department_id": e["department_id"], "shift": e["shift"],
                    "shift_premium": shift_prem, "overtime_hours": ot_hours,
                    "severance_provision": severance, "meal_allowance": meal,
                    "transport_allowance": transport, "stamp_duty": stamp,
                    "unemployment_employee": unemp_emp, "unemployment_employer": unemp_er,
                })
                gross_t += gross
                ded_t += sgk_emp + unemp_emp + tax + other_ded
                net_t += net
                cost_t += cost
                ot_t += ot
            self.add("payroll_runs", {
                "id": rid, "run_no": f"BRD-{year}{m:02d}", "period_year": year,
                "period_month": m, "period_date": mend, "country": self.home_cc,
                "pay_date": min(add_days(mend, 5), today), "currency": self.base_ccy,
                "employee_count": len(active), "gross_total": money(gross_t),
                "employee_deductions_total": money(ded_t), "net_total": money(net_t),
                "employer_cost_total": money(cost_t), "employer_cost_base": money(cost_t),
                "status": "Muhasebeleştirildi",
                "employer_cost_eur": self.eur(cost_t, mend),
                "employer_cost_usd": self.usd(cost_t, mend),
                "overtime_total": money(ot_t), "department_id": None,
            })

    # ========================================================= duran varlıklar ==
    def gen_fixed_assets(self):
        """Tezgahlar ithal edilir ve EUR ile fiyatlanır; TL maliyeti alım
        tarihindeki kurdan sabitlenir (tarihi maliyet)."""
        r = self.rng.stream("varlik")
        today = self._today()
        prod_dept = self._dept_by_name.get("Üretim")
        for mch in self.rows("machines"):
            aid = self.nid("fixed_assets")
            acq = mch["commissioned_date"]
            fx = self.try_per("EUR", acq) if acq >= self.start_date else \
                self.try_per("EUR", self.start_date)
            cost_eur = mch["_cost_eur"] * r.jitter(1.0, 0.18)
            cost = money(cost_eur * fx)
            self.add("fixed_assets", {
                "id": aid, "asset_no": f"DV-{aid:05d}",
                "name": f"{mch['manufacturer']} {mch['model']} ({mch['code']})",
                "category": mch["_asset_category"], "department_id": prod_dept,
                "warehouse_id": None, "vendor_id": (r.choice(self._vpool(
                    "Tezgah ve Makina Tedarikçisi")) if self._vend else None),
                "acquisition_date": acq, "acquisition_cost": cost,
                "useful_life_years": 12, "salvage_value": money(cost * 0.05),
                "method": "Normal Amortisman", "status": "Kullanımda",
                "disposal_date": None, "disposal_proceeds": None,
                "accumulated_depreciation": 0.0, "net_book_value": cost,
                "serial_no": mch["serial_no"], "machine_id": mch["id"],
                "acquisition_cost_eur": money(cost_eur), "fx_rate": round(fx, 6),
                "currency": "EUR",
            })
            mch["fixed_asset_id"] = aid
        for spec in self.s.get("fixed_assets", []):
            for _ in range(int(spec.get("count", 1))):
                aid = self.nid("fixed_assets")
                acq_y = r.randint(max(self.p.start_year - 6, 2012), self.p.end_year())
                acq = min(random_date_in_month(r, acq_y, r.randint(1, 12)), today)
                fx = self.try_per("EUR", max(acq, self.start_date))
                cost_eur = r.jitter((float(spec["cost_eur_min"]) +
                                     float(spec["cost_eur_max"])) / 2, 0.28)
                cost = money(cost_eur * fx)
                self.add("fixed_assets", {
                    "id": aid, "asset_no": f"DV-{aid:05d}", "name": spec["name"],
                    "category": spec["category"],
                    "department_id": self._dept_by_name.get(spec.get("department")),
                    "warehouse_id": (r.choice(self._wh_all) if r.chance(0.4) else None),
                    "vendor_id": r.choice(list(self._vend)), "acquisition_date": acq,
                    "acquisition_cost": cost,
                    "useful_life_years": int(spec["useful_life_years"]),
                    "salvage_value": money(cost * float(spec.get("salvage_pct", 0)) / 100.0),
                    "method": "Normal Amortisman", "status": "Kullanımda",
                    "disposal_date": None, "disposal_proceeds": None,
                    "accumulated_depreciation": 0.0, "net_book_value": cost,
                    "serial_no": f"{spec['category'][:2].upper()}{r.randint(100000, 999999)}",
                    "machine_id": None, "acquisition_cost_eur": money(cost_eur),
                    "fx_rate": round(fx, 6), "currency": "EUR",
                })
        self._depreciate()
        self._prod_asset_ids = {a["id"] for a in self.rows("fixed_assets")
                                if a["machine_id"] or a["category"] in
                                ("Tezgah ve Üretim Makinaları", "Üretim Yardımcı Ekipmanı",
                                 "Kalite Ölçüm Ekipmanı", "Bina ve Tesis")}

    # ================================================================ giderler ==
    def _add_expense(self, r, spec, cat, d, amt_base, dept_id, vendor_id, ccy, source,
                     ref_type=None, ref_id=None, emp_id=None, desc=None, is_cash=True,
                     wc_id=None):
        eid = self.nid("expenses")
        fxr = self.fx(ccy, d)
        amount = money(amt_base * fxr)
        vat = money(amt_base * self.vat_rate) if (spec.get("vat", True) and is_cash) else 0.0
        paid = is_cash and (d < add_days(self._today(), -40) or r.chance(0.7))
        self.add("expenses", {
            "id": eid, "expense_no": f"GDR-{d.year}-{eid:07d}", "expense_date": d,
            "period_year": d.year, "period_month": d.month, "category_id": cat["id"],
            "department_id": dept_id, "vendor_id": vendor_id, "employee_id": emp_id,
            "warehouse_id": None,
            "cost_center": (self._dept_row[dept_id]["cost_center"] if dept_id else None),
            "description": desc or cat["name"], "currency": ccy, "amount": amount,
            "fx_rate": self._fxr(fxr), "amount_base": amt_base, "tax_amount": vat,
            "total_base": money(amt_base + vat),
            "payment_method": ("Otomatik Ödeme Talimatı" if source == "purchased" else
                               "Havale / EFT" if source == "payroll" else "Nakit Dışı"),
            "status": "Ödendi" if paid else "Açık", "source": source,
            "reference_type": ref_type, "reference_id": ref_id,
            "amount_eur": self.eur(amt_base, d), "amount_usd": self.usd(amt_base, d),
            "fx_rate_eur": round(self.try_per("EUR", d), 6),
            "fx_rate_usd": round(self.try_per("USD", d), 6),
            "work_center_id": wc_id,
        })
        return eid

    def gen_expenses(self):
        """Brüt kârın altındaki tüm maliyetler tek tabloda; `source` kolonu
        satın alınan gider / personel / amortisman / lojistik / finansman /
        vergi ayrımını yapar, böylece hiçbir kalem iki kez sayılmaz."""
        r = self.rng.stream("gider")
        depts = self._dept_by_name
        for cat in self.rows("expense_categories"):
            spec = self._exp_cat[cat["code"]]
            if spec.get("source", "purchased") != "purchased":
                continue
            annual_eur = float(spec["annual_amount_eur"])
            var = float(spec.get("variability_pct", 0)) / 100.0
            freq = spec.get("frequency", "monthly")
            dept_id = depts.get(spec.get("department"))
            pool = self._vpool(*(spec.get("vendor_types") or [])) if spec.get("vendor_types") \
                else list(self._vend)
            ccy = spec.get("currency", self.base_ccy)
            rev_final = self.p.revenue_for_year(self.p.years - 1)
            for yi, year, m in self.months():
                if freq == "quarterly" and m not in (3, 6, 9, 12):
                    continue
                if freq == "annual" and m != int(spec.get("month", 12)):
                    continue
                periods = {"monthly": 12, "quarterly": 4, "annual": 1}[freq]
                d = self._clamp(random_date_in_month(r, year, m))
                rev_idx = self.p.revenue_for_year(yi) / rev_final
                # TL cinsinden gider kur + reel artışla birlikte büyür
                amt_base = (annual_eur / periods * ((1 - var) + var * rev_idx)
                            * self.try_per("EUR", d) * self._drift(d, self.real_cost_drift))
                amt_base = money(amt_base * r.jitter(1.0, float(spec.get("noise", 0.13))))
                if amt_base <= 0:
                    continue
                self._add_expense(r, spec, cat, d, amt_base, dept_id,
                                  (r.choice(pool) if pool else None), ccy, "purchased")
        self._payroll_expenses_tr(r)
        self._depreciation_expenses_tr(r)
        self._logistics_expenses_tr(r)
        self._finance_expenses_tr(r)
        self._tax_expenses_tr(r)

    def _payroll_expenses_tr(self, r):
        """Direkt üretim operatörlerinin ücreti SMM içinde (mamul maliyetinde)
        taşınır; geri kalan tüm personel maliyeti gider olarak kaydedilir."""
        emp = {e["id"]: e for e in self.rows("employees")}
        buckets = {}
        self._direct_labor_by_month = {}
        for it in self.rows("payroll_items"):
            e = emp[it["employee_id"]]
            key = (it["period_year"], it["period_month"])
            if e["job_family"] == "Üretim":
                self._direct_labor_by_month[key] = self._direct_labor_by_month.get(key, 0.0) \
                    + it["employer_cost"]
                continue
            dept = self._dept_row[e["department_id"]]
            code = dept.get("_payroll_category") or "GYG-PER"
            b = buckets.setdefault((key[0], key[1], e["department_id"], code),
                                   [0.0, it["period_date"]])
            b[0] += it["employer_cost"]
        for (y, m, dept_id, code), (amt, pdate) in sorted(buckets.items()):
            cat = self._cat_row.get(code)
            if not cat:
                continue
            self._add_expense(r, self._exp_cat[code], cat, pdate, money(amt), dept_id,
                              None, self.base_ccy, "payroll", "payroll_run", None,
                              desc=f"Personel maliyeti {y}-{m:02d} "
                                   f"({self._dept_row[dept_id]['name']})")

    def _depreciation_expenses_tr(self, r):
        by_period = {}
        for de in self.rows("depreciation_entries"):
            is_prod = de["asset_id"] in self._prod_asset_ids
            key = (de["period_year"], de["period_month"], de["period_date"], is_prod)
            by_period[key] = by_period.get(key, 0.0) + de["depreciation_amount"]
        for (y, m, pd, is_prod), amt in sorted(by_period.items()):
            code = "GUG-AMR" if is_prod else "GYG-AMR"
            cat = self._cat_row.get(code)
            if not cat or amt <= 0:
                continue
            self._add_expense(r, self._exp_cat[code], cat, pd, money(amt),
                              self._dept_by_name.get("Üretim" if is_prod
                                                     else "Finans ve Muhasebe"),
                              None, self.base_ccy, "depreciation", "depreciation", None,
                              desc=f"{'Üretim' if is_prod else 'İdari'} amortisman "
                                   f"{y}-{m:02d}", is_cash=False)

    def _logistics_expenses_tr(self, r):
        dept = self._dept_by_name.get("Lojistik ve Sevkiyat")
        frt = self._cat_row.get("PSD-NAK")
        if frt:
            by_month = {}
            for s in self.rows("shipments"):
                key = (s["ship_date"].year, s["ship_date"].month)
                by_month[key] = by_month.get(key, 0.0) + max(
                    0.0, s["cost_base"] - s["billed_to_customer"])
            for (y, m), amt in sorted(by_month.items()):
                if amt <= 0:
                    continue
                d = self._clamp(date(y, m, min(28, days_in_month(y, m))))
                self._add_expense(r, self._exp_cat["PSD-NAK"], frt, d, money(amt), dept,
                                  None, self.base_ccy, "logistics", "shipments", None,
                                  desc=f"Sevkiyat, nakliye ve ambalaj gideri {y}-{m:02d}")
        gum = self._cat_row.get("PSD-GUM")
        if gum:
            by_month = {}
            for cd in self.rows("customs_declarations"):
                key = (cd["decl_date"].year, cd["decl_date"].month)
                by_month[key] = by_month.get(key, 0.0) + cd["duty_amount"] + cd["broker_fee"]
            for (y, m), amt in sorted(by_month.items()):
                if amt <= 0:
                    continue
                d = self._clamp(date(y, m, min(28, days_in_month(y, m))))
                self._add_expense(r, self._exp_cat["PSD-GUM"], gum, d, money(amt), dept,
                                  None, self.base_ccy, "logistics", "customs", None,
                                  desc=f"Gümrükleme, müşavirlik ve resim {y}-{m:02d}")

    def _finance_expenses_tr(self, r):
        """İşletme sermayesi kredisi faizi. Türkiye'de faiz oranları yıllar
        içinde çok değiştiği için yıl bazında verilir."""
        cat = self._cat_row.get("FIN-FAZ")
        if not cat:
            return
        dept = self._dept_by_name.get("Finans ve Muhasebe")
        rates = {int(k): float(v) for k, v in
                 self.t.get("loan_rate_by_year", {}).items()}
        ratio = float(self.t.get("working_capital_loan_ratio", 0.11))
        for yi, year, m in self.months():
            rate = rates.get(year, 0.35)
            monthly_rev = self.p.revenue_for_year(yi) * self.p.seasonality[m - 1] / 12.0
            loan = monthly_rev * 12.0 * ratio
            amt = money(loan * rate / 12.0)
            if amt <= 0:
                continue
            d = self._clamp(date(year, m, min(28, days_in_month(year, m))))
            self._add_expense(r, self._exp_cat["FIN-FAZ"], cat, d, amt, dept, None,
                              self.base_ccy, "financing", "kredi", None,
                              desc=f"İşletme sermayesi kredi faizi {year}-{m:02d}",
                              is_cash=True)

    def _tax_expenses_tr(self, r):
        cat = self._cat_row.get("VRG-KUR")
        if not cat:
            return
        dept = self._dept_by_name.get("Finans ve Muhasebe")
        rate = float(self.t.get("income_tax_rate", 0.25))
        so_year = {o["id"]: (o["order_date"].year, o["order_date"].month)
                   for o in self.rows("sales_orders") if o["status"] != SO_CANCEL}
        gp_month = {}
        for l in self.rows("sales_order_lines"):
            ym = so_year.get(l["order_id"])
            if ym:
                gp_month[ym] = gp_month.get(ym, 0.0) + l["line_margin_base"]
        gp = {}
        for (y, m), v in gp_month.items():
            gp[y] = gp.get(y, 0.0) + v
        opex = {}
        for e in self.rows("expenses"):
            opex[e["period_year"]] = opex.get(e["period_year"], 0.0) + e["amount_base"]
        for pay in self.rows("payments"):
            y = pay["payment_date"].year
            opex[y] = opex.get(y, 0.0) - pay["fx_gain_loss"]
        for rt in self.rows("returns"):
            if rt["status"] != "Reddedildi":
                y = rt["return_date"].year
                opex[y] = opex.get(y, 0.0) + rt["refund_amount_base"]
        for y in sorted(gp):
            ebt = gp[y] - opex.get(y, 0.0)
            if ebt <= 0:
                continue
            charge = ebt * rate
            months = [(m, v) for (yy, m), v in gp_month.items() if yy == y and v > 0]
            total_gp = sum(v for _, v in months) or 1.0
            for m, v in sorted(months):
                amt = money(charge * v / total_gp)
                if amt <= 0:
                    continue
                d = self._clamp(date(y, m, min(28, days_in_month(y, m))))
                self._add_expense(r, self._exp_cat["VRG-KUR"], cat, d, amt, dept, None,
                                  self.base_ccy, "tax", "kurumlar_vergisi", None,
                                  desc=f"Kurumlar vergisi karşılığı {y}-{m:02d}",
                                  is_cash=False)

    def gen_budgets(self):
        r = self.rng.stream("butce")
        actual = {}
        for e in self.rows("expenses"):
            key = (e["period_year"], e["period_month"], e["department_id"], e["category_id"])
            actual[key] = actual.get(key, 0.0) + e["amount_base"]
        for (y, m, dept, cat), amt in sorted(actual.items(),
                                             key=lambda kv: (kv[0][0], kv[0][1])):
            self.add("budgets", {
                "id": self.nid("budgets"), "fiscal_year": y, "period_month": m,
                "department_id": dept, "expense_category_id": cat,
                "budget_amount": money(amt * r.jitter(1.03, 0.17)),
                "budget_type": "Faaliyet Bütçesi", "approved_by": "Mali İşler Direktörü",
            })

    # ==================================================== stok, kasa, yevmiye ==
    def gen_stock_moves(self):
        r = self.rng.stream("stok")
        n_months = max(1, (self.p.years - 1) * 12 + self.end_month)
        open_months = float(self.t.get("opening_stock_months", 1.6))

        # açılış stokları (hammadde ve mamul)
        rm_used = {}
        for c in self.rows("production_consumption"):
            rm_used[c["raw_material_id"]] = rm_used.get(c["raw_material_id"], 0.0) \
                + float(c["consumed_qty"])
        rm_recv = {}
        for l in self.rows("purchase_order_lines"):
            if l["item_type"] != "raw_material" or not l["received_qty"]:
                continue
            if self._po_by_id[l["po_id"]]["status"] == PO_CANCEL:
                continue
            rm_recv[l["item_id"]] = rm_recv.get(l["item_id"], 0.0) + float(l["received_qty"])
        for rm_id, qty in rm_used.items():
            # açılış stoğu, dönem boyunca sarfın tedariki aştığı durumu da kapatır;
            # aksi halde tek bir iptal edilen sipariş kalemi stok bakiyesini eksiye düşürür
            deficit = qty - rm_recv.get(rm_id, 0.0)
            oq = round(max(1.0, qty * open_months / n_months,
                           deficit * 1.05 if deficit > 0 else 0.0), 3)
            cost = self._rm[rm_id]["unit_cost"] / self.try_per("EUR", self._today()) \
                * self.try_per("EUR", self.start_date)
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": self.start_date,
                "item_type": "Hammadde", "item_id": rm_id, "warehouse_id": self._wh_rm,
                "move_type": MOVE_IN, "qty": oq, "unit_cost": round(cost, 4),
                "reference_type": "Açılış Stoğu", "reference_id": None,
                "machine_unit_id": None, "value_base": money(oq * cost), "lot_ref": None,
            })
        sold = {}
        for l in self.rows("sales_order_lines"):
            if self._order_by_id[l["order_id"]]["status"] == SO_CANCEL:
                continue
            sold[l["product_id"]] = sold.get(l["product_id"], 0.0) + float(l["qty"])
        made = {}
        for w in self.rows("production_orders"):
            if w["status"] == WO_DONE and w["produced_qty"]:
                made[w["product_id"]] = made.get(w["product_id"], 0.0) + float(w["produced_qty"])
        for pid, qty in sold.items():
            deficit = qty - made.get(pid, 0.0)
            oq = round(max(1.0, qty * open_months / n_months,
                           deficit * 1.05 if deficit > 0 else 0.0), 2)
            cost = self._prod[pid]["unit_cost"] / self.try_per("EUR", self._today()) \
                * self.try_per("EUR", self.start_date)
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": self.start_date,
                "item_type": "Mamul", "item_id": pid, "warehouse_id": self._wh_fg,
                "move_type": MOVE_IN, "qty": oq, "unit_cost": round(cost, 4),
                "reference_type": "Açılış Stoğu", "reference_id": None,
                "machine_unit_id": None, "value_base": money(oq * cost), "lot_ref": None,
            })

        # hammadde girişleri (mal kabul)
        for l in self.rows("purchase_order_lines"):
            if l["item_type"] != "raw_material" or not l["received_qty"]:
                continue
            po = self._po_by_id[l["po_id"]]
            if po["status"] == PO_CANCEL:
                continue
            unit_b = l["line_total_base"] / max(float(l["qty"]), 1.0)
            self.add("stock_moves", {
                "id": self.nid("stock_moves"),
                "move_date": po["received_date"] or po["order_date"],
                "item_type": "Hammadde", "item_id": l["item_id"],
                "warehouse_id": po["warehouse_id"], "move_type": MOVE_IN,
                "qty": l["received_qty"], "unit_cost": round(unit_b, 4),
                "reference_type": "Satınalma Siparişi", "reference_id": l["po_id"],
                "machine_unit_id": None,
                "value_base": money(unit_b * float(l["received_qty"])), "lot_ref": None,
            })
        # üretim sarfiyatı
        for c in self.rows("production_consumption"):
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": c["issue_date"],
                "item_type": "Hammadde", "item_id": c["raw_material_id"],
                "warehouse_id": c["warehouse_id"], "move_type": MOVE_OUT,
                "qty": c["consumed_qty"], "unit_cost": c["unit_cost"],
                "reference_type": "İş Emri", "reference_id": c["production_order_id"],
                "machine_unit_id": None, "value_base": c["total_cost"],
                "lot_ref": c["lot_no"],
            })
        # mamul girişi
        for w in self.rows("production_orders"):
            if w["status"] != WO_DONE or not w["produced_qty"]:
                continue
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": w["actual_end"] or w["actual_start"],
                "item_type": "Mamul", "item_id": w["product_id"],
                "warehouse_id": w["warehouse_id"], "move_type": MOVE_IN,
                "qty": w["produced_qty"], "unit_cost": w["unit_cost"],
                "reference_type": "İş Emri", "reference_id": w["id"],
                "machine_unit_id": None,
                "value_base": money(w["produced_qty"] * w["unit_cost"]),
                "lot_ref": w["lot_no"],
            })
        # sevkiyat
        for l in self.rows("sales_order_lines"):
            o = self._order_by_id[l["order_id"]]
            if o["status"] == SO_CANCEL:
                continue
            self.add("stock_moves", {
                "id": self.nid("stock_moves"),
                "move_date": o["shipped_date"] or o["order_date"],
                "item_type": "Mamul", "item_id": l["product_id"],
                "warehouse_id": o["warehouse_id"], "move_type": MOVE_OUT, "qty": l["qty"],
                "unit_cost": round(l["line_cogs_base"] / max(float(l["qty"]), 1.0), 4),
                "reference_type": "Satış Siparişi", "reference_id": l["order_id"],
                "machine_unit_id": None, "value_base": l["line_cogs_base"], "lot_ref": None,
            })
        # müşteri iadeleri
        for rt in self.rows("returns"):
            if rt["status"] == "Reddedildi":
                continue
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": rt["return_date"],
                "item_type": "Mamul", "item_id": rt["product_id"],
                "warehouse_id": self._wh_fg, "move_type": MOVE_IN, "qty": rt["qty"],
                "unit_cost": 0, "reference_type": "Müşteri İadesi", "reference_id": rt["id"],
                "machine_unit_id": None, "value_base": 0, "lot_ref": None,
            })

    def gen_bank(self):
        r = self.rng.stream("banka")
        ev = []
        for p in self.rows("payments"):
            ev.append((p["payment_date"], "Giriş", p["amount_base"], "Ticari Hesap (TL)",
                       "Müşteri Tahsilatı", "payment", p["id"],
                       self._cust_name_map.get(p["customer_id"], "Müşteri"),
                       f"Fatura tahsilatı {p['currency']} {p['amount']:,.2f}", p["currency"]))
        for vp in self.rows("vendor_payments"):
            ev.append((vp["payment_date"], "Çıkış", vp["amount_base"], "Ticari Hesap (TL)",
                       "Tedarikçi Ödemesi", "vendor_payment", vp["id"],
                       self._vend_name_map.get(vp["vendor_id"], "Tedarikçi"),
                       f"Fatura ödemesi {vp['currency']} {vp['amount']:,.2f}",
                       vp["currency"]))
        cat_by_id = {c["id"]: c for c in self.rows("expense_categories")}
        for e in self.rows("expenses"):
            if e["source"] in ("depreciation",) or e["status"] != "Ödendi":
                continue
            cat = cat_by_id[e["category_id"]]
            ev.append((e["expense_date"], "Çıkış", e["total_base"], "Ticari Hesap (TL)",
                       cat["expense_group"], "expense", e["id"],
                       self._vend_name_map.get(e["vendor_id"], cat["name"]),
                       e["description"], self.base_ccy))
        for (y, m), amt in sorted(getattr(self, "_direct_labor_by_month", {}).items()):
            d = self._clamp(date(y, m, min(28, days_in_month(y, m))))
            ev.append((d, "Çıkış", money(amt), "Maaş Hesabı (TL)", "Direkt İşçilik",
                       "payroll_direct", None, "Üretim personeli",
                       f"Direkt üretim personeli ücret ödemesi {y}-{m:02d}", self.base_ccy))
        ev.sort(key=lambda x: (x[0], x[6] or 0))
        balance = float(self.t.get("opening_cash", 26000000))
        for (d, direction, amount, account, category, rtype, rid, cp, desc, ccy) in ev:
            balance += amount if direction == "Giriş" else -amount
            self.add("bank_transactions", {
                "id": self.nid("bank_transactions"), "txn_date": d, "account": account,
                "direction": direction, "counterparty": cp, "reference_type": rtype,
                "reference_id": rid, "amount": money(amount),
                "balance_after": money(balance), "currency": self.base_ccy, "fx_rate": 1.0,
                "amount_base": money(amount), "category": category, "description": desc,
                "amount_eur": self.eur(amount, d), "amount_usd": self.usd(amount, d),
                "bank_name": ("Ziraat Bankası" if "Maaş" in account else "İş Bankası"),
                "account_currency": ccy,
            })

    # --- tekdüzen hesap planına göre yevmiye kayıtları ------------------------
    def _je(self, d, journal, ref_type, ref_id, lines, memo="", dept=None):
        total_d = round(sum(x[1] for x in lines), 2)
        total_c = round(sum(x[2] for x in lines), 2)
        if abs(total_d - total_c) > 0.005:
            code, dr, cr = lines[-1]
            diff = round(total_d - total_c, 2)
            lines[-1] = (code, dr, round(cr + diff, 2)) if diff > 0 else \
                (code, round(dr - diff, 2), cr)
        self._entry_no += 1
        no = f"YV-{d.year}-{self._entry_no:08d}"
        fx_e = round(self.try_per("EUR", d), 6)
        fx_u = round(self.try_per("USD", d), 6)
        ln = 0
        for (code, dr, cr) in lines:
            if abs(dr) < 0.005 and abs(cr) < 0.005:
                continue
            ln += 1
            self.add("gl_entries", {
                "id": self.nid("gl_entries"), "entry_date": d, "account_code": code,
                "account_name": self._acct.get(code, code), "debit": money(dr),
                "credit": money(cr), "reference_type": ref_type, "reference_id": ref_id,
                "entry_no": no, "journal": journal, "line_no": ln, "department_id": dept,
                "currency": self.base_ccy, "fx_rate": 1.0, "debit_base": money(dr),
                "credit_base": money(cr), "period_year": d.year, "period_month": d.month,
                "memo": memo, "fx_rate_eur": fx_e, "fx_rate_usd": fx_u,
            })

    def gen_gl(self):
        sol_by_order = self._so_lines_by_order
        # --- satış ve satılan mamul maliyeti
        for inv in self.rows("invoices"):
            o = self._order_by_id[inv["order_id"]]
            rev_acct = "601" if o["is_export"] else "600"
            entry = [("120", inv["total_base"], 0.0),
                     (rev_acct, 0.0, inv["subtotal_base"])]
            if inv["tax_base"]:
                entry.append(("391", 0.0, inv["tax_base"]))
            self._je(inv["invoice_date"], "Satış", "invoice", inv["id"], entry,
                     memo=f"{inv['invoice_no']} {inv['currency']} {inv['total']:,.2f}")
            cogs = sum(l["line_cogs_base"] for l in sol_by_order.get(o["id"], []))
            if cogs:
                self._je(inv["invoice_date"], "Satılan Mamul Maliyeti", "invoice", inv["id"],
                         [("620", money(cogs), 0.0), ("152", 0.0, money(cogs))],
                         memo=f"{inv['invoice_no']} satış maliyeti")
        # --- tahsilat ve kur farkı
        for p in self.rows("payments"):
            inv = self._inv_by_id[p["invoice_id"]]
            at_inv = money(p["amount"] * inv["fx_rate"])
            entry = [("102", p["amount_base"], 0.0), ("120", 0.0, at_inv)]
            diff = money(p["amount_base"] - at_inv)
            if abs(diff) >= 0.01:
                entry.append(("646", 0.0, diff) if diff > 0 else ("656", -diff, 0.0))
            self._je(p["payment_date"], "Kasa/Banka Tahsilat", "payment", p["id"], entry,
                     memo=f"{p['payment_no']} {p['currency']} {p['amount']:,.2f}")
        # --- satınalma ve tedarikçi ödemeleri
        for vb in self.rows("vendor_invoices"):
            sub_b = money(vb["total_base"] - (vb["tax"] * vb["fx_rate"] if vb["fx_rate"] else 0))
            vat_b = money(vb["total_base"] - sub_b)
            entry = [("150", sub_b, 0.0)]
            if vat_b:
                entry.append(("191", vat_b, 0.0))
            entry.append(("320", 0.0, vb["total_base"]))
            self._je(vb["bill_date"], "Satınalma", "vendor_invoice", vb["id"], entry,
                     memo=f"{vb['bill_no']} {vb['currency']} {vb['total']:,.2f}")
        for vp in self.rows("vendor_payments"):
            self._je(vp["payment_date"], "Kasa/Banka Ödeme", "vendor_payment", vp["id"],
                     [("320", vp["amount_base"], 0.0), ("102", 0.0, vp["amount_base"])],
                     memo=f"{vp['payment_no']} {vp['currency']} {vp['amount']:,.2f}")
        # --- üretim: malzeme, fason ve takım maliyetinin mamule aktarılması
        for w in self.rows("production_orders"):
            if w["status"] != WO_DONE:
                continue
            direct_mat = money(w["material_cost"] + w["tooling_cost"] + w["subcontract_cost"])
            if direct_mat > 0:
                self._je(w["actual_end"] or w["actual_start"], "Üretim", "production_order",
                         w["id"], [("152", direct_mat, 0.0), ("150", 0.0, direct_mat)],
                         memo=f"{w['wo_no']} malzeme, fason ve takım maliyeti")
        # --- direkt üretim işçiliği (mamul maliyetine yüklenir)
        for (y, m), amt in sorted(getattr(self, "_direct_labor_by_month", {}).items()):
            d = self._clamp(date(y, m, min(28, days_in_month(y, m))))
            self._je(d, "Üretim", "payroll_direct", None,
                     [("152", money(amt), 0.0), ("102", 0.0, money(amt))],
                     memo=f"Direkt üretim işçiliği {y}-{m:02d}")
        # --- faaliyet giderleri
        cat_by_id = {c["id"]: c for c in self.rows("expense_categories")}
        for e in self.rows("expenses"):
            cat = cat_by_id[e["category_id"]]
            if e["source"] == "depreciation":
                credit = ("257", 0.0, e["amount_base"])
            elif e["source"] == "tax":
                credit = ("370", 0.0, e["amount_base"])
            elif e["status"] == "Ödendi":
                credit = ("102", 0.0, e["total_base"])
            else:
                credit = ("320", 0.0, e["total_base"])
            entry = [(cat["account_code"], e["amount_base"], 0.0)]
            if e["tax_amount"] and e["status"] == "Ödendi" and e["source"] == "purchased":
                entry.append(("191", e["tax_amount"], 0.0))
            entry.append(credit)
            self._je(e["expense_date"], cat["expense_group"], "expense", e["id"], entry,
                     memo=e["description"], dept=e["department_id"])
        # --- satıştan iadeler
        for rt in self.rows("returns"):
            if rt["status"] == "Reddedildi":
                continue
            amt = rt["refund_amount_base"]
            self._je(rt["return_date"], "Satıştan İadeler", "return", rt["id"],
                     [("610", amt, 0.0), ("120", 0.0, amt)],
                     memo=f"{rt['return_no']} - {rt['reason']}")

    # =================================================================== IoT ==
    def gen_iot(self):
        """Tezgah telemetrisi. Yalnızca son `iot_days` gün üretilir; tüm geçmiş
        için saniyelik veri tutmak bir demo veritabanını gereksiz büyütür."""
        r = self.rng.stream("iot")
        days = int(self.t.get("iot_days", 60))
        step_h = int(self.t.get("iot_sample_hours", 2))
        metrics = self.t.get("iot_metrics", [])
        machines = [m for m in self.rows("machines") if m["status"] == "Aktif"]
        limit = int(self.t.get("iot_machines", 40))
        machines = machines[:limit]
        if not machines or not metrics:
            return
        end = self._today()
        shifts = self.t.get("shifts", ["1. Vardiya", "2. Vardiya", "3. Vardiya"])
        for mch in machines:
            drift = r.jitter(1.0, 0.12)
            for dd in range(days):
                d = add_days(end, -dd)
                for hh in range(0, 24, step_h):
                    shift = shifts[0] if 8 <= hh < 16 else (shifts[1] if 16 <= hh < 24
                                                            else shifts[2])
                    night = 0.94 if hh < 8 else 1.0
                    for mt in metrics:
                        val = float(mt["base"]) * drift * night * (
                            1 + (r.rand() - 0.5) * 2 * float(mt["sigma"]))
                        if mt["metric"].endswith("_pct"):
                            val = min(100.0, max(0.0, val))
                        self.add("iot_readings", {
                            "id": self.nid("iot_readings"), "source_type": "Tezgah",
                            "source_id": mch["id"],
                            "reading_ts": f"{d.isoformat()} {hh:02d}:00:00",
                            "metric": mt["metric"], "value": round(val, 4),
                            "unit": mt["unit"], "work_center_id": mch["work_center_id"],
                            "shift": shift,
                        })
