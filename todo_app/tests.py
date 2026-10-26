"""
Test suite untuk todo_app/views.py.

Cara menjalankan (letakkan file ini di todo_app/test.py):
    python manage.py test todo_app.test
    python manage.py test todo_app.test.TeachingTests.test_search_filters   # satu tes saja
(pytest: `pytest todo_app/test.py`, karena nama test.py tidak dikenali pola bawaan pytest)

Strategi:
- View dipanggil langsung dengan RequestFactory, jadi tes tidak bergantung pada nama URL
  (kecuali login yang memang memakai namespace `todo_app:`).
- Pola CRUD HTMX yang identik pada Client/Contract/Payment/Teaching diuji sekali lewat
  `CrudMixin`, lalu dipakai ulang oleh empat TestCase; logika pencarian/filter diuji per entitas.
- Logika queryset & pagination diuji langsung lewat view.get_queryset()/get_context_data(),
  sehingga cepat dan tidak bergantung pada isi template.
- Jika model Anda mewajibkan field lain, cukup sesuaikan blok "PABRIK DATA" di bawah.
"""
import itertools
import json
import unittest
from contextlib import nullcontext
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from . import views
from .forms import ClientForm, ContractForm, PaymentForm, TeachingForm
from .models import Client, Contract, Payment, Teaching, TeachingRecord

User = get_user_model()
rf = RequestFactory()
_seq = itertools.count(1)


# ======================================================================
# PABRIK DATA  (sesuaikan di sini bila model punya field wajib lain)
# ======================================================================
def aware(y, m, d, hh=12, mm=0):
    return timezone.make_aware(datetime(y, m, d, hh, mm))


def default_choice(model, field_name):
    """Nilai default field, atau pilihan pertamanya (dipakai untuk field ber-choices)."""
    field = model._meta.get_field(field_name)
    default = field.get_default()
    return default if default not in (None, "") else field.flatchoices[0][0]


def make_client(nama="Budi", **kw):
    n = next(_seq)
    kw.setdefault("kontak", f"0812{n:07d}")
    kw.setdefault("kota", "Bogor")
    kw.setdefault("alamat", "Jl. Mawar 1")
    return Client.objects.create(nama=nama, **kw)


def make_contract(client=None, **kw):
    kw.setdefault("tipe_kontrak", "Privat")
    kw.setdefault("total_pertemuan", 10)
    kw.setdefault("total_biaya", 1_000_000)
    kw.setdefault("keterangan", "Kontrak uji")
    kw.setdefault("contract_status", "Berjalan")
    return Contract.objects.create(client=client or make_client(), **kw)


def make_payment(contract=None, **kw):
    kw.setdefault("tanggal", aware(2025, 1, 15))
    kw.setdefault("total", 500_000)
    return Payment.objects.create(contract=contract or make_contract(), **kw)


def make_teaching(kontrak=None, **kw):
    kontrak = kontrak or make_contract()
    kw.setdefault("client", kontrak.client)
    kw.setdefault("day_of_week", 0)
    kw.setdefault("start_time", time(9, 0))
    kw.setdefault("end_time", time(10, 0))
    kw.setdefault("materi", "Hiragana")
    return Teaching.objects.create(kontrak=kontrak, **kw)


def make_record(teaching, tanggal=None, **kw):
    kw.setdefault("materi_realisasi", "Materi uji")
    return TeachingRecord.objects.create(
        kontrak=teaching.kontrak, teaching=teaching,
        tanggal_pelaksanaan=tanggal or timezone.now(), **kw,
    )


def pks(qs):
    return set(qs.values_list("pk", flat=True))


# ======================================================================
# BASE
# ======================================================================
class ViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="guru", password="rahasia123")

    def build(self, method="get", data=None, htmx=False, user=True):
        extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
        if method == "get":
            request = rf.get("/", data or {}, **extra)
        elif method == "delete":
            request = rf.delete("/", **extra)
        else:
            request = rf.post("/", data or {}, **extra)
        request.user = self.user if user else AnonymousUser()
        return request

    def call(self, view, method="get", data=None, htmx=False, user=True, **kwargs):
        """Panggil view, render TemplateResponse bila perlu, kembalikan response."""
        response = view.as_view()(self.build(method, data, htmx, user), **kwargs)
        if hasattr(response, "render") and not response.is_rendered:
            response.render()
        return response

    def queryset_of(self, view_cls, params=None):
        view = view_cls()
        view.setup(self.build("get", params, htmx=True))
        return view.get_queryset()

    def context_of(self, view_cls, params=None):
        view = view_cls()
        view.setup(self.build("get", params, htmx=True))
        view.object_list = view.get_queryset()
        return view.get_context_data()

    def assert_trigger(self, response, toast_type, text, event=None):
        payload = json.loads(response["HX-Trigger"])
        if event:
            self.assertIn(event, payload)
        self.assertEqual(payload["showToast"]["type"], toast_type)
        self.assertIn(text, payload["showToast"]["message"])
        return payload

    def assert_login_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response.url)


# ======================================================================
# MIXIN: pola CRUD HTMX yang sama untuk Client / Contract / Payment / Teaching
# ======================================================================
class CrudMixin:
    # --- konfigurasi, diisi oleh subclass ---
    list_view = create_view = edit_view = delete_view = search_view = None
    model = form_class = None
    entity = ""                      # -> event "<entity>ListChanged"
    add_form_id = ""                 # HX-Retarget saat create invalid
    edit_form_prefix = ""            # HX-Retarget saat edit invalid (+pk)
    list_template = list_partial = edit_template = ""
    create_ok_template = None        # None => response sukses berupa body kosong

    def make_obj(self): raise NotImplementedError
    def create_data(self): raise NotImplementedError
    def invalid_data(self): return {}
    def edit_data(self, obj): raise NotImplementedError
    def assert_edited(self, obj): raise NotImplementedError

    @property
    def event(self):
        return f"{self.entity}ListChanged"

    # ---------------- create ----------------
    def test_create_get_renders_modal(self):
        self.assertEqual(self.call(self.create_view).status_code, 200)

    def test_create_valid(self):
        data = self.create_data()
        before = self.model.objects.count()
        ctx = (self.assertTemplateUsed(self.create_ok_template)
               if self.create_ok_template else nullcontext())
        with ctx:
            response = self.call(self.create_view, "post", data, htmx=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.model.objects.count(), before + 1)
        self.assert_trigger(response, "alert-success", "berhasil ditambahkan", self.event)
        if not self.create_ok_template:
            self.assertEqual(response.content, b"")

    def test_create_invalid(self):
        before = self.model.objects.count()
        response = self.call(self.create_view, "post", self.invalid_data(), htmx=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.model.objects.count(), before)
        self.assertEqual(response["HX-Retarget"], self.add_form_id)
        self.assertEqual(response["HX-Reswap"], "outerHTML")
        payload = self.assert_trigger(response, "alert-error", "Gagal menyimpan")
        self.assertNotIn(self.event, payload)

    # ---------------- edit ----------------
    def test_edit_get_renders_modal(self):
        obj = self.make_obj()
        with self.assertTemplateUsed(self.edit_template):
            response = self.call(self.edit_view, pk=obj.pk)
        self.assertEqual(response.status_code, 200)

    def test_edit_valid(self):
        obj = self.make_obj()
        response = self.call(self.edit_view, "post", self.edit_data(obj), htmx=True, pk=obj.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assert_trigger(response, "alert-success", "berhasil diperbarui", self.event)
        obj.refresh_from_db()
        self.assert_edited(obj)

    def test_edit_invalid(self):
        obj = self.make_obj()
        response = self.call(self.edit_view, "post", self.invalid_data(), htmx=True, pk=obj.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Retarget"], f"{self.edit_form_prefix}{obj.pk}")
        self.assertEqual(response["HX-Reswap"], "outerHTML")
        payload = self.assert_trigger(response, "alert-error", "Gagal memperbarui")
        self.assertNotIn(self.event, payload)

    def test_edit_missing_returns_404(self):
        with self.assertRaises(Http404):
            self.call(self.edit_view, "post", self.invalid_data(), htmx=True, pk=999999)

    # ---------------- delete ----------------
    def test_delete_htmx(self):
        obj = self.make_obj()
        response = self.call(self.delete_view, "delete", htmx=True, pk=obj.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertFalse(self.model.objects.filter(pk=obj.pk).exists())
        self.assert_trigger(response, "alert-warning", "berhasil dihapus", self.event)

    def test_delete_missing_returns_404(self):
        with self.assertRaises(Http404):
            self.call(self.delete_view, "delete", htmx=True, pk=999999)

    # ---------------- list ----------------
    def test_list_full_page_and_htmx_partial(self):
        with self.assertTemplateUsed(self.list_template):
            self.assertEqual(self.call(self.list_view).status_code, 200)
        with self.assertTemplateUsed(self.list_partial):
            self.assertEqual(self.call(self.list_view, htmx=True).status_code, 200)

    def test_list_and_search_context_pagination(self):
        for _ in range(25):
            self.make_obj()
        for view in (self.list_view, self.search_view):
            with self.subTest(view=view.__name__):
                page1 = self.context_of(view)
                self.assertEqual(page1["page_obj"].paginator.count, 25)
                self.assertEqual(len(page1["page_obj"]), 20)
                self.assertEqual(list(page1["custom_page_range"]), [1, 2])
                self.assertEqual(len(self.context_of(view, {"page": 2})["page_obj"]), 5)

    def test_list_context_has_form(self):
        form = self.context_of(self.list_view)["form"]
        form_cls = form if isinstance(form, type) else type(form)
        self.assertTrue(issubclass(form_cls, self.form_class))

    # ---------------- search (umum) ----------------
    def test_search_requires_htmx(self):
        with self.assertRaises(Http404):
            self.call(self.search_view, data={"search": "x"}, htmx=False)

    def test_search_renders_partial(self):
        with self.assertTemplateUsed(self.list_partial):
            self.assertEqual(self.call(self.search_view, htmx=True).status_code, 200)

    def test_search_empty_query_returns_all(self):
        self.make_obj(); self.make_obj()
        for query in ("", "   "):
            with self.subTest(query=query):
                self.assertEqual(pks(self.queryset_of(self.search_view, {"search": query})),
                                 pks(self.model.objects.all()))

    # ---------------- login required ----------------
    def test_login_required(self):
        cases = [
            (self.list_view, "get", False, {}),
            (self.create_view, "get", False, {}),
            (self.create_view, "post", False, {}),
            (self.edit_view, "get", False, {"pk": 1}),
            (self.delete_view, "delete", False, {"pk": 1}),
            (self.search_view, "get", True, {}),
        ]
        for view, method, htmx, kwargs in cases:
            with self.subTest(view=view.__name__, method=method):
                self.assert_login_redirect(
                    self.call(view, method, htmx=htmx, user=False, **kwargs))

    def test_search_anonymous_without_htmx_is_404_first(self):
        # dispatch() milik view search menolak non-HTMX sebelum pengecekan login
        with self.assertRaises(Http404):
            self.call(self.search_view, htmx=False, user=False)


# ======================================================================
# CLIENT
# ======================================================================
class ClientTests(CrudMixin, ViewTestCase):
    list_view, create_view, edit_view = views.ListClientView, views.CreateClientView, views.EditClientView
    delete_view, search_view = views.DeleteClientView, views.SearchClientView
    model, form_class, entity = Client, ClientForm, "client"
    add_form_id, edit_form_prefix = "#add-client-form", "#edit-client-form-"
    list_template, list_partial = "client/list.html", "client/table-container.html"
    edit_template, create_ok_template = "client/edit-modal.html", "client/form-fields.html"

    def make_obj(self): return make_client()
    def invalid_data(self): return {"nama": ""}

    def create_data(self):
        return {"nama": "Siti", "kontak": "08123456789", "kota": "Bogor", "alamat": "Jl. Melati"}

    def edit_data(self, obj):
        return {"nama": "Siti Updated", "kontak": obj.kontak, "kota": obj.kota, "alamat": obj.alamat}

    def assert_edited(self, obj): self.assertEqual(obj.nama, "Siti Updated")

    def test_search_filters(self):
        a = make_client("Budi Santoso", alamat="Jl. Mawar", kontak="0811111")
        b = make_client("Sari Dewi", alamat="Jl. Melati", kontak="0822222")
        cases = {"budi": {a}, "  BUDI  ": {a}, "melati": {b}, "0822222": {b},
                 "082": set(),  # kontak dicocokkan persis, bukan parsial
                 "tidak-ada": set()}
        for query, expected in cases.items():
            with self.subTest(query=query):
                got = pks(self.queryset_of(views.SearchClientView, {"search": query}))
                self.assertEqual(got, {o.pk for o in expected})


# ======================================================================
# CONTRACT
# ======================================================================
class ContractTests(CrudMixin, ViewTestCase):
    list_view, create_view, edit_view = views.ListContractView, views.CreateContractView, views.EditContractView
    delete_view, search_view = views.DeleteContractView, views.SearchContractView
    model, form_class, entity = Contract, ContractForm, "contract"
    add_form_id, edit_form_prefix = "#add-contract-form", "#edit-contract-form-"
    list_template, list_partial = "contract/list.html", "contract/table-container.html"
    edit_template, create_ok_template = "contract/edit-modal.html", "contract/form-fields.html"

    def make_obj(self): return make_contract()

    def create_data(self):
        return {"client": make_client().pk, "tipe_kontrak": "Privat", "total_pertemuan": 10,
                "total_biaya": 1_500_000, "keterangan": "Kontrak baru"}

    def edit_data(self, obj):
        return {"client": obj.client_id, "tipe_kontrak": obj.tipe_kontrak, "total_pertemuan": 12,
                "total_biaya": 2_000_000, "keterangan": "Diubah",
                "pembayaran": default_choice(Contract, "pembayaran"), "contract_status": "Berjalan"}

    def assert_edited(self, obj):
        self.assertEqual(int(obj.total_biaya), 2_000_000)
        self.assertEqual(obj.total_pertemuan, 12)

    def test_list_filter_by_status(self):
        running = make_contract(contract_status="Berjalan")
        done = make_contract(contract_status="Habis")
        for status, expected in (("Berjalan", running), ("Habis", done)):
            with self.subTest(status=status):
                ctx = self.context_of(views.ListContractView, {"contract_status": status})
                self.assertEqual(pks(ctx["page_obj"].paginator.object_list), {expected.pk})
                self.assertEqual(ctx["current_contract_status"], status)
        self.assertEqual(self.context_of(views.ListContractView)["current_contract_status"], "")

    def test_list_filter_by_pembayaran(self):
        choices = [c for c, _ in Contract._meta.get_field("pembayaran").flatchoices]
        if len(choices) < 2:
            self.skipTest("field pembayaran punya kurang dari 2 pilihan")
        make_contract(pembayaran=choices[0])
        b = make_contract(pembayaran=choices[1])
        ctx = self.context_of(views.ListContractView, {"pembayaran": choices[1]})
        self.assertEqual(pks(ctx["page_obj"].paginator.object_list), {b.pk})
        self.assertEqual(ctx["current_pembayaran"], choices[1])

    def test_list_filters_are_combined(self):
        a = make_contract(contract_status="Berjalan")
        make_contract(contract_status="Habis")
        qs = self.queryset_of(views.ListContractView, {"contract_status": "Berjalan", "pembayaran": ""})
        self.assertEqual(pks(qs), {a.pk})

    def test_search_by_client_name(self):
        a = make_contract(make_client("Budi Santoso"))
        make_contract(make_client("Sari Dewi"))
        for query in ("budi", " BUDI "):
            with self.subTest(query=query):
                self.assertEqual(pks(self.queryset_of(views.SearchContractView, {"search": query})), {a.pk})
        self.assertEqual(pks(self.queryset_of(views.SearchContractView, {"search": "zzz"})), set())


# ======================================================================
# PAYMENT
# ======================================================================
class PaymentTests(CrudMixin, ViewTestCase):
    list_view, create_view, edit_view = views.ListPaymentView, views.CreatePaymentView, views.EditPaymentView
    delete_view, search_view = views.DeletePaymentView, views.SearchPaymentView
    model, form_class, entity = Payment, PaymentForm, "payment"
    add_form_id, edit_form_prefix = "#add-payment-form", "#edit-payment-form-"
    list_template, list_partial = "payment/list.html", "payment/table-container.html"
    edit_template, create_ok_template = "payment/edit-modal.html", "payment/form-fields.html"

    def make_obj(self): return make_payment()
    def invalid_data(self): return {"total": ""}

    def create_data(self):
        return {"contract": make_contract().pk, "tanggal_0": "2025-02-10",
                "tanggal_1": "09:30", "total": 250_000}

    def edit_data(self, obj):
        return {"contract": obj.contract_id, "tanggal_0": "2025-03-05",
                "tanggal_1": "10:15", "total": 300_000}

    def assert_edited(self, obj): self.assertEqual(int(obj.total), 300_000)

    def test_search_filters(self):
        jan = make_payment(make_contract(make_client("Budi Santoso")), tanggal=aware(2025, 1, 15))
        feb = make_payment(make_contract(make_client("Sari Dewi")), tanggal=aware(2025, 2, 15))
        cases = {"budi": {jan}, "SARI": {feb}, "tidak-ada": set(),
                 "::1": {jan}, "::2": {feb}, "::12": set()}   # "::<bulan>" memfilter tanggal__month
        kode = getattr(jan, "kode_payment", None)
        if kode:
            cases[kode] = {jan}
        for query, expected in cases.items():
            with self.subTest(query=query):
                got = pks(self.queryset_of(views.SearchPaymentView, {"search": query}))
                self.assertEqual(got, {o.pk for o in expected})


# ======================================================================
# TEACHING
# ======================================================================
class TeachingTests(CrudMixin, ViewTestCase):
    list_view, create_view, edit_view = views.ListTeachingView, views.CreateTeachingView, views.EditTeachingView
    delete_view, search_view = views.DeleteTeachingView, views.SearchTeachingView
    model, form_class, entity = Teaching, TeachingForm, "teaching"
    add_form_id, edit_form_prefix = "#add-teach-form", "#edit-teach-form-"
    list_template, list_partial = "teaching/list.html", "teaching/table-container.html"
    edit_template, create_ok_template = "teaching/edit-modal.html", None   # sukses = body kosong

    def make_obj(self): return make_teaching()

    def create_data(self):
        kontrak = make_contract()
        return {"client": kontrak.client_id, "kontrak": kontrak.pk, "day_of_week": 0,
                "start_time": "09:00", "end_time": "10:00", "materi": "Hiragana"}

    def edit_data(self, obj):
        return {"client": obj.client_id, "kontrak": obj.kontrak_id, "day_of_week": 2,
                "start_time": "13:00", "end_time": "14:00", "materi": "Katakana",
                "status_teaching": "on"}

    def assert_edited(self, obj):
        self.assertEqual((obj.materi, obj.day_of_week), ("Katakana", 2))

    def test_search_filters(self):
        a = make_teaching(make_contract(make_client("Budi Santoso", kontak="0811111")),
                          day_of_week=0, start_time=time(9, 0))
        b = make_teaching(make_contract(make_client("Sari Dewi", kontak="0822222")),
                          day_of_week=2, start_time=time(14, 0))
        c = make_teaching(make_contract(make_client("Rudi", kontak="0833333")),
                          day_of_week=4, start_time=time(9, 30))
        cases = {
            "budi": {a}, "  BUDI  ": {a}, "0822222": {b}, "tidak-ada": set(),
            "senin": {a}, "SENIN": {a}, "monday": {a}, "rabu": {b}, "wednesday": {b},
            "jumat": {c}, "jum'at": {c}, "minggu": set(),
            "::jam=9": {a, c}, "::jam=14": {b}, "::JAM=14": {b},
            "::jam=99": set(), "::jam=abc": set(), "::jam=": set(),
        }
        if a.kontrak.kode_kontrak:
            cases[a.kontrak.kode_kontrak] = {a}
        for query, expected in cases.items():
            with self.subTest(query=query):
                got = pks(self.queryset_of(views.SearchTeachingView, {"search": query}))
                self.assertEqual(got, {o.pk for o in expected})

    def test_search_digit_matches_day_of_week(self):
        b = make_teaching(day_of_week=2)
        make_teaching(day_of_week=5)
        # angka 0-6 juga ikut mencocokkan jam mulai (icontains), jadi cek keanggotaan
        self.assertIn(b.pk, pks(self.queryset_of(views.SearchTeachingView, {"search": "2"})))


# ======================================================================
# RECORD TEACHING (POST dari modal jadwal)
# ======================================================================
class RecordTeachingTests(ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.privat = make_contract(tipe_kontrak="Privat", total_pertemuan=2)
        cls.teaching = make_teaching(cls.privat, materi="Hiragana")

    def record(self, teaching=None, **data):
        teaching = teaching or self.teaching
        return self.call(views.RecordTeachingView, "post", data, htmx=True, pk=teaching.pk)

    def test_get_renders_record_modal(self):
        with self.assertTemplateUsed("teaching/record-modal.html"):
            response = self.call(views.RecordTeachingView, pk=self.teaching.pk)
        self.assertEqual(response.status_code, 200)

    def test_get_context(self):
        view = views.RecordTeachingView()
        context = view.get_context_data(self.teaching, self.build("get", {"page": 1}))
        self.assertEqual(context["teaching"], self.teaching)
        self.assertEqual(context["page_obj"].number, 1)
        self.assertEqual(context["forloop"]["counter0"], 0)
        self.assertRegex(context["now_iso"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")

    def test_missing_teaching_is_404(self):
        with self.assertRaises(Http404):
            self.call(views.RecordTeachingView, pk=999999)
        with self.assertRaises(Http404):
            self.call(views.RecordTeachingView, "post", {}, htmx=True, pk=999999)

    def test_privat_success_uses_defaults(self):
        response = self.record()
        self.assertEqual((response.status_code, response.content), (200, b""))
        payload = self.assert_trigger(response, "alert-success", "Privat", "teachingListChanged")
        rec = TeachingRecord.objects.get()
        self.assertEqual((rec.teaching, rec.kontrak), (self.teaching, self.privat))
        self.assertEqual(rec.materi_realisasi, "Hiragana")          # default = materi jadwal
        self.assertFalse(rec.is_rescheduled)
        self.assertLess(abs(timezone.now() - rec.tanggal_pelaksanaan), timedelta(minutes=1))

    def test_privat_with_custom_input(self):
        self.record(materi_realisasi="Katakana", is_rescheduled="on",
                    tanggal_pelaksanaan="2025-03-10T14:30")
        rec = TeachingRecord.objects.get()
        self.assertEqual(rec.materi_realisasi, "Katakana")
        self.assertTrue(rec.is_rescheduled)
        self.assertEqual(timezone.localtime(rec.tanggal_pelaksanaan).strftime("%Y-%m-%dT%H:%M"),
                         "2025-03-10T14:30")

    def test_privat_final_session_marks_contract_done(self):
        contract = make_contract(tipe_kontrak="Privat", total_pertemuan=1)
        self.record(make_teaching(contract))
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, "Habis")

    def test_privat_quota_full_is_blocked(self):
        contract = make_contract(tipe_kontrak="Privat", total_pertemuan=1)
        teaching = make_teaching(contract)
        make_record(teaching)
        response = self.record(teaching)
        self.assertEqual(TeachingRecord.objects.filter(teaching=teaching).count(), 1)
        payload = json.loads(response["HX-Trigger"])
        self.assertNotIn("teachingListChanged", payload)
        self.assertIn(payload["showToast"]["type"], ("alert-warning", "alert-error"))

    def test_finished_contract_is_blocked(self):
        contract = make_contract(contract_status="Habis")
        response = self.record(make_teaching(contract))
        self.assertEqual(TeachingRecord.objects.count(), 0)
        payload = self.assert_trigger(response, "alert-error", "sudah selesai atau habis")
        self.assertNotIn("teachingListChanged", payload)

    def test_institusi_ignores_quota(self):
        contract = make_contract(tipe_kontrak="Institusi", total_pertemuan=1)
        teaching = make_teaching(contract)
        for _ in range(3):
            response = self.record(teaching)
        self.assertEqual(TeachingRecord.objects.filter(teaching=teaching).count(), 3)
        self.assert_trigger(response, "alert-success", "Institusi", "teachingListChanged")

    def test_unknown_contract_type_is_rejected(self):
        contract = make_contract(tipe_kontrak="Lain")
        response = self.record(make_teaching(contract))
        self.assertEqual(TeachingRecord.objects.count(), 0)
        self.assert_trigger(response, "alert-error", "tidak dikenali")

    def test_login_required(self):
        for method in ("get", "post"):
            with self.subTest(method=method):
                self.assert_login_redirect(
                    self.call(views.RecordTeachingView, method, user=False, pk=self.teaching.pk))


# ======================================================================
# TEACHING RECORD: list, search, delete
# ======================================================================
class TeachingRecordTests(ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.t1 = make_teaching(make_contract(make_client("Budi Santoso", kontak="0811111")),
                               day_of_week=0, start_time=time(9, 0))    # jadwal Senin 09:00
        cls.t2 = make_teaching(make_contract(make_client("Sari Dewi", kontak="0822222")),
                               day_of_week=2, start_time=time(14, 0))   # jadwal Rabu 14:00
        # Sengaja "bersilangan": r1 dijadwalkan Senin tapi dilaksanakan hari Rabu (15 Jan 2025),
        # r2 dijadwalkan Rabu tapi dilaksanakan hari Senin (13 Jan 2025).
        cls.r1 = make_record(cls.t1, aware(2025, 1, 15))
        cls.r2 = make_record(cls.t2, aware(2025, 1, 13))

    def search(self, query):
        return pks(self.queryset_of(views.SearchTeachingRecordView, {"search": query}))

    # ---------------- list ----------------
    def test_list_full_page_and_htmx_partial(self):
        with self.assertTemplateUsed("teaching/record-list.html"):
            self.assertEqual(self.call(views.ListTeachingRecordView).status_code, 200)
        with self.assertTemplateUsed("teaching/record-table-container.html"):
            self.assertEqual(self.call(views.ListTeachingRecordView, htmx=True).status_code, 200)

    def test_list_and_search_pagination(self):
        for _ in range(23):
            make_record(self.t1)    # total 25 record
        for view in (views.ListTeachingRecordView, views.SearchTeachingRecordView):
            with self.subTest(view=view.__name__):
                page1 = self.context_of(view)
                self.assertEqual(page1["page_obj"].paginator.count, 25)
                self.assertEqual(len(page1["page_obj"]), 20)
                self.assertEqual(list(page1["custom_page_range"]), [1, 2])
                self.assertEqual(len(self.context_of(view, {"page": 2})["page_obj"]), 5)

    # ---------------- search ----------------
    def test_search_requires_htmx(self):
        with self.assertRaises(Http404):
            self.call(views.SearchTeachingRecordView, data={"search": "x"}, htmx=False)

    def test_search_renders_partial(self):
        with self.assertTemplateUsed("teaching/record-table-container.html"):
            response = self.call(views.SearchTeachingRecordView, htmx=True)
        self.assertEqual(response.status_code, 200)

    def test_search_empty_returns_all(self):
        for query in ("", "   "):
            self.assertEqual(self.search(query), {self.r1.pk, self.r2.pk})

    def test_search_general_fields(self):
        cases = {"budi": {self.r1}, "  BUDI ": {self.r1}, "sari": {self.r2},
                 "0822222": {self.r2}, "tidak-ada": set()}
        kode = self.t1.kontrak.kode_kontrak
        if kode:
            cases[kode] = {self.r1}
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {o.pk for o in expected})

    def test_search_day_name_filters_by_tanggal_pelaksanaan(self):
        # Tanpa prefix: hari dari tanggal_pelaksanaan (r2 = Senin, r1 = Rabu)
        cases = {"senin": {self.r2}, "SENIN": {self.r2}, "monday": {self.r2},
                 "rabu": {self.r1}, "wednesday": {self.r1}, "selasa": set(), "minggu": set()}
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {o.pk for o in expected})

    def test_search_digit_uses_tanggal_pelaksanaan(self):
        # 0 = Senin -> r2 ; 2 = Rabu -> r1 (angka juga ikut mencocokkan jam, jadi cek keanggotaan)
        self.assertIn(self.r2.pk, self.search("0"))
        self.assertIn(self.r1.pk, self.search("2"))

    def test_search_jadwal_filters_by_teaching_day(self):
        # Dengan "::jadwal=": hari jadwal (teaching__day_of_week), kebalikan dari hasil tanpa prefix
        cases = {"::jadwal=senin": {self.r1}, "::JADWAL=Rabu": {self.r2}, "::jadwal= senin ": {self.r1},
                 "::jadwal=monday": {self.r1}, "::jadwal=0": {self.r1}, "::jadwal=2": {self.r2},
                 "::jadwal=selasa": set(), "::jadwal=xyz": set(), "::jadwal=9": set(), "::jadwal=": set()}
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {o.pk for o in expected})

    def test_search_jam_filters_by_teaching_start_hour(self):
        cases = {"::jam=9": {self.r1}, "::jam=14": {self.r2}, "::JAM=14": {self.r2},
                 "::jam=24": set(), "::jam=-1": set(), "::jam=abc": set(), "::jam=": set()}
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {o.pk for o in expected})

    # ---------------- delete ----------------
    def test_delete_htmx(self):
        response = self.call(views.DeleteTeachingRecordView, "delete", htmx=True, pk=self.r1.pk)
        self.assertEqual((response.status_code, response.content), (200, b""))
        self.assertFalse(TeachingRecord.objects.filter(pk=self.r1.pk).exists())
        self.assertTrue(TeachingRecord.objects.filter(pk=self.r2.pk).exists())
        self.assert_trigger(response, "alert-warning", "berhasil dihapus", "RecordTeachingListChanged")

    def test_delete_missing_returns_404(self):
        with self.assertRaises(Http404):
            self.call(views.DeleteTeachingRecordView, "delete", htmx=True, pk=999999)

    def test_delete_restores_contract_status(self):
        """Integrasi: sesi terakhir dicatat -> kontrak 'Habis'; record dihapus -> kembali 'Berjalan'."""
        contract = make_contract(tipe_kontrak="Privat", total_pertemuan=1)
        teaching = make_teaching(contract)
        self.call(views.RecordTeachingView, "post", {}, htmx=True, pk=teaching.pk)
        record = TeachingRecord.objects.get(teaching=teaching)
        self.call(views.DeleteTeachingRecordView, "delete", htmx=True, pk=record.pk)
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, "Berjalan")

    # ---------------- login required ----------------
    def test_login_required(self):
        cases = [(views.ListTeachingRecordView, "get", False),
                 (views.SearchTeachingRecordView, "get", True),
                 (views.DeleteTeachingRecordView, "delete", False)]
        for view, method, htmx in cases:
            with self.subTest(view=view.__name__):
                kwargs = {"pk": self.r1.pk} if method == "delete" else {}
                self.assert_login_redirect(self.call(view, method, htmx=htmx, user=False, **kwargs))


# ======================================================================
# AUTOCOMPLETE (django-autocomplete-light)
# ======================================================================
class AutocompleteTests(ViewTestCase):
    def results(self, view, user=True, **params):
        response = view.as_view()(self.build("get", params, user=user))
        self.assertEqual(response.status_code, 200)
        return {int(r["id"]) for r in json.loads(response.content)["results"]}

    def test_client_autocomplete(self):
        a = make_client("Budi Santoso", alamat="Jl. Mawar", kontak="0811111")
        b = make_client("Sari Dewi", alamat="Jl. Melati", kontak="0822222")
        view = views.ClientFormAutocomplete
        self.assertEqual(self.results(view), {a.pk, b.pk})
        cases = {"budi": {a.pk}, "MELATI": {b.pk}, "0822222": {b.pk}, "082": set(), "zzz": set()}
        for q, expected in cases.items():
            with self.subTest(q=q):
                self.assertEqual(self.results(view, q=q), expected)

    def test_contract_autocomplete(self):
        c1, c2 = make_client("Budi Santoso"), make_client("Sari Dewi")
        k1, k2, k3 = make_contract(c1), make_contract(c1), make_contract(c2)
        view = views.ContractFormAutocomplete
        self.assertEqual(self.results(view), {k1.pk, k2.pk, k3.pk})
        # forward=['client'] mempersempit hasil ke kontrak milik klien tsb
        forward = json.dumps({"client": str(c1.pk)})
        self.assertEqual(self.results(view, forward=forward), {k1.pk, k2.pk})
        self.assertEqual(self.results(view, q="sari"), {k3.pk})
        self.assertEqual(self.results(view, q="sari", forward=forward), set())  # kombinasi forward + q
        if k1.kode_kontrak:
            self.assertEqual(self.results(view, q=k1.kode_kontrak, forward=forward), {k1.pk})

    def test_anonymous_gets_nothing(self):
        make_contract()
        for view in (views.ClientFormAutocomplete, views.ContractFormAutocomplete):
            with self.subTest(view=view.__name__):
                self.assertEqual(self.results(view, user=False), set())


# ======================================================================
# AUTHENTICATION
# ======================================================================
class AuthTests(ViewTestCase):
    def test_login_page_renders(self):
        self.assertEqual(self.client.get(reverse("todo_app:login")).status_code, 200)

    def test_login_success_redirects_to_teaching_list(self):
        response = self.client.post(reverse("todo_app:login"),
                                    {"username": "guru", "password": "rahasia123"})
        self.assertRedirects(response, reverse("todo_app:teaching_list"), fetch_redirect_response=False)

    def test_login_wrong_password_stays_on_page(self):
        response = self.client.post(reverse("todo_app:login"),
                                    {"username": "guru", "password": "salah"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("todo_app:login"))
        self.assertRedirects(response, reverse("todo_app:teaching_list"), fetch_redirect_response=False)

    def test_logout_anonymous_redirects_to_login(self):
        request = rf.get("/logout/")
        request.user = AnonymousUser()
        response = views.logout_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("todo_app:login"), response.url)

    def test_logout_authenticated_clears_user_and_redirects(self):
        request = rf.get("/logout/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        request.user = self.user
        response = views.logout_view(request)
        self.assertEqual(response.url, reverse("todo_app:login"))
        self.assertFalse(request.user.is_authenticated)


class GenerateUniqueUsernameTests(TestCase):
    def test_format_strips_spaces(self):
        with patch.object(views.random, "randint", return_value=123):
            self.assertEqual(views.generate_unique_username("Budi Santoso"), "BudiSantoso_123")

    def test_retries_when_username_taken(self):
        User.objects.create_user("abc_111", password="x")
        with patch.object(views.random, "randint", side_effect=[111, 222]):
            self.assertEqual(views.generate_unique_username("abc"), "abc_222")


# ======================================================================
# BUG YANG TERDETEKSI DI views.py  (expectedFailure = lulus selama bug masih ada;
# begitu diperbaiki, runner melapor "unexpected success" -> hapus dekoratornya)
# ======================================================================
class KnownIssueTests(ViewTestCase):
    @unittest.expectedFailure
    def test_payment_search_with_non_numeric_month_should_not_crash(self):
        # "::abc" -> tanggal__month="abc" melempar ValueError (HTTP 500)
        response = self.call(views.SearchPaymentView, data={"search": "::abc"}, htmx=True)
        self.assertEqual(response.status_code, 200)

    @unittest.expectedFailure
    def test_record_with_invalid_datetime_should_not_crash(self):
        # fromisoformat("bukan-tanggal") melempar ValueError (HTTP 500)
        teaching = make_teaching()
        response = self.call(views.RecordTeachingView, "post",
                             {"tanggal_pelaksanaan": "bukan-tanggal"}, htmx=True, pk=teaching.pk)
        self.assertEqual(response.status_code, 200)

    @unittest.expectedFailure
    def test_non_htmx_delete_should_redirect(self):
        # delete() sudah menghapus objek, lalu super().delete() memanggil get_object() lagi -> 404
        obj = make_client()
        response = self.call(views.DeleteClientView, "delete", htmx=False, pk=obj.pk)
        self.assertEqual(response.status_code, 302)
