"""
Unit tests for views.py.

Place next to views.py (e.g. todo_app/test_views.py) and run:
    python manage.py test todo_app.test_views

IMPORTANT - URL names:
    urls.py was not provided. Names that appear in views.py (login,
    teaching_list, client_list, contract_list, payment_list,
    teaching_record_list) are certain. Every other name is a best guess and
    is isolated in the URL_NAMES mapping below - adjust it to match urls.py.

No external HTTP/third-party calls exist in these modules (the WhatsApp link
is only a built string), so mocking is used for time (timezone.now), randomness
and ModelForm validation instead.
"""
import json
from datetime import datetime, time
from unittest import mock
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .. import views
from ..models import Client, Contract, Payment, Teaching, TeachingRecord

User = get_user_model()

APP_NAMESPACE = "todo_app"

# Logical name -> url name inside the namespace. EDIT THESE to match urls.py.
URL_NAMES = {
    # confirmed from views.py
    "login": "login",
    "teaching_list": "teaching_list",
    "client_list": "client_list",
    "contract_list": "contract_list",
    "payment_list": "payment_list",
    "teaching_record_list": "teaching_record_list",
    # guesses
    "logout": "logout",
    "client_create": "client_create",
    "client_edit": "client_edit",
    "client_delete": "client_delete",
    "search_client": "search_client",
    "contract_create": "contract_create",
    "contract_edit": "contract_edit",
    "contract_delete": "contract_delete",
    "search_contract": "search_contract",
    "payment_create": "payment_create",
    "payment_edit": "payment_edit",
    "payment_delete": "payment_delete",
    "search_payment": "search_payment",
    "teaching_create": "teaching_create",
    "teaching_edit": "teaching_edit",
    "teaching_delete": "teaching_delete",
    "search_teaching": "search_teaching",
    "teaching_record": "teaching_record",              # RecordTeachingView (pk)
    "teaching_record_delete": "teaching_record_delete",
    "search_teaching_record": "search_teaching_record",
}

HTMX = {"HTTP_HX_REQUEST": "true"}  # -> request.headers["HX-Request"] == "true"

FAST_HASHER = override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)


def u(name, **kwargs):
    return reverse(f"{APP_NAMESPACE}:{URL_NAMES[name]}", kwargs=kwargs or None)


def aware(year, month, day, hour=10, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def hx_trigger(response):
    return json.loads(response["HX-Trigger"])


def toast(response):
    return hx_trigger(response)["showToast"]


def pks(response, context_key):
    return {obj.pk for obj in response.context[context_key]}


# --------------------------------------------------------------------------- #
# Shared fixtures
# --------------------------------------------------------------------------- #
@FAST_HASHER
class BaseViewTestCase(TestCase):
    """Builds one shared dataset (created once per class) and logs in per test.

    Fixture notes (relied on by the search tests):
      * kontak values / kode_kontrak values contain no digit '2' and no day
        abbreviations, so searches for '2', 'senin', 'rabu', ... are deterministic.
      * Teaching slots: Mon 10:00, Wed 14:00, Fri 14:30.
    """

    @classmethod
    def setUpTestData(cls):
        cls.password = "pass12345"
        cls.user = User.objects.create_user(username="admin", password=cls.password)

        cls.client_a = Client.objects.create(
            nama="Budi Santoso", kontak="0811", alamat="Jl. Melati Bogor"
        )
        cls.client_b = Client.objects.create(
            nama="Siti Aminah", kontak="0899", alamat="Jl. Kenanga Depok"
        )

        cls.contract_a = Contract.objects.create(
            client=cls.client_a, total_biaya=1_000_000, total_pertemuan=10,
            kode_kontrak="AAAA",
        )
        cls.contract_b = Contract.objects.create(
            client=cls.client_b, total_biaya=2_000_000, total_pertemuan=0,
            tipe_kontrak="Institusi", kode_kontrak="BBBB",
        )

        cls.t_mon = Teaching.objects.create(
            client=cls.client_a, kontrak=cls.contract_a, day_of_week=0,
            start_time=time(10, 0), end_time=time(11, 0), materi="Hiragana",
        )
        cls.t_wed = Teaching.objects.create(
            client=cls.client_b, kontrak=cls.contract_b, day_of_week=2,
            start_time=time(14, 0), end_time=time(15, 0), materi="Katakana",
        )
        cls.t_fri = Teaching.objects.create(
            client=cls.client_a, kontrak=cls.contract_a, day_of_week=4,
            start_time=time(14, 30), end_time=time(15, 30),
        )

        cls.p_mar = Payment.objects.create(
            contract=cls.contract_a, tanggal=aware(2025, 3, 15), total=500_000
        )
        cls.p_may = Payment.objects.create(
            contract=cls.contract_b, tanggal=aware(2025, 5, 10), total=700_000
        )

        # 2025-01-06 is a Monday.
        cls.r_mon = TeachingRecord.objects.create(
            kontrak=cls.contract_a, teaching=cls.t_mon,
            tanggal_pelaksanaan=aware(2025, 1, 6, 10),          # Monday
        )
        cls.r_tue = TeachingRecord.objects.create(
            kontrak=cls.contract_b, teaching=cls.t_wed,
            tanggal_pelaksanaan=aware(2025, 1, 7, 14),          # Tuesday
        )
        cls.r_resched = TeachingRecord.objects.create(
            kontrak=cls.contract_a, teaching=cls.t_mon,
            tanggal_pelaksanaan=aware(2025, 1, 8, 10),          # Wednesday
            is_rescheduled=True,
        )

    def setUp(self):
        self.client.force_login(self.user)


# --------------------------------------------------------------------------- #
# About page (public) - no URL name needed, no template rendering
# --------------------------------------------------------------------------- #
class AboutViewTests(TestCase):
    def _view(self, query=""):
        request = RequestFactory().get("/about/" + query)
        view = views.AboutView()
        view.setup(request)
        return view

    def test_default_style_is_sakura(self):
        view = self._view()
        self.assertEqual(view.get_template_names(), ["about_sakura.html"])

    def test_known_styles_select_matching_template(self):
        for style, template in views.AboutView.TEMPLATES.items():
            with self.subTest(style=style):
                view = self._view(f"?style={style}")
                self.assertEqual(view.get_template_names(), [template])

    def test_unknown_style_falls_back_to_default(self):
        view = self._view("?style=hacker")
        self.assertEqual(view.get_template_names(), ["about_sakura.html"])
        self.assertEqual(view.get_context_data()["style"], "sakura")

    def test_context_contains_about_data_and_whatsapp_url(self):
        context = self._view("?style=neon").get_context_data()
        profile = views.ABOUT["profile"]
        self.assertEqual(context["style"], "neon")
        self.assertEqual(context["profile"], profile)
        self.assertEqual(
            context["wa_url"],
            f"https://wa.me/{profile['whatsapp']}?text={quote(profile['wa_message'])}",
        )

    def test_whatsapp_message_is_url_encoded(self):
        wa_url = self._view().get_context_data()["wa_url"]
        self.assertNotIn(" ", wa_url)
        self.assertTrue(wa_url.startswith("https://wa.me/"))


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
class AuthenticationTests(BaseViewTestCase):
    def test_login_redirects_to_teaching_list(self):
        self.client.logout()
        response = self.client.post(
            u("login"), {"username": "admin", "password": self.password}
        )
        self.assertRedirects(
            response, u("teaching_list"), fetch_redirect_response=False
        )

    def test_login_with_wrong_password_stays_on_page(self):
        self.client.logout()
        response = self.client.post(
            u("login"), {"username": "admin", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_already_authenticated_user_is_redirected_away_from_login(self):
        response = self.client.get(u("login"))
        self.assertRedirects(
            response, u("teaching_list"), fetch_redirect_response=False
        )

    def test_logout_clears_session_and_redirects_to_login(self):
        response = self.client.get(u("logout"))
        self.assertRedirects(response, u("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_login(self):
        self.client.logout()
        response = self.client.get(u("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(u("login"), response["Location"])

    def test_list_pages_require_login(self):
        self.client.logout()
        for name in ("client_list", "contract_list", "payment_list",
                     "teaching_list", "teaching_record_list"):
            with self.subTest(view=name):
                response = self.client.get(u(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn("next=", response["Location"])

    def test_htmx_endpoints_require_login(self):
        self.client.logout()
        # Note: these views check the HX header *before* the login mixin,
        # so a logged-out HTMX request is the meaningful case to assert.
        for name, kwargs in (
            ("client_create", {}),
            ("contract_create", {}),
            ("payment_create", {}),
            ("teaching_create", {}),
            ("search_client", {}),
            ("search_teaching_record", {}),
        ):
            with self.subTest(view=name):
                response = self.client.get(u(name, **kwargs), **HTMX)
                self.assertEqual(response.status_code, 302)


# --------------------------------------------------------------------------- #
# HTMX-only guards
# --------------------------------------------------------------------------- #
class HtmxGuardTests(BaseViewTestCase):
    def test_create_views_reject_non_htmx_with_400(self):
        for name in ("client_create", "contract_create",
                     "payment_create", "teaching_create"):
            with self.subTest(view=name, method="GET"):
                self.assertEqual(self.client.get(u(name)).status_code, 400)
            with self.subTest(view=name, method="POST"):
                self.assertEqual(self.client.post(u(name), {}).status_code, 400)

    def test_edit_views_reject_non_htmx_with_400(self):
        targets = {
            "client_edit": self.client_a,
            "contract_edit": self.contract_a,
            "payment_edit": self.p_mar,
            "teaching_edit": self.t_mon,
        }
        for name, obj in targets.items():
            with self.subTest(view=name):
                self.assertEqual(
                    self.client.get(u(name, pk=obj.pk)).status_code, 400
                )

    def test_search_views_return_404_for_non_htmx(self):
        for name in ("search_client", "search_contract", "search_payment",
                     "search_teaching", "search_teaching_record"):
            with self.subTest(view=name):
                self.assertEqual(self.client.get(u(name)).status_code, 400)

    def test_delete_record_rejects_non_htmx(self):
        response = self.client.delete(u("teaching_record_delete", pk=self.r_mon.pk))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(TeachingRecord.objects.filter(pk=self.r_mon.pk).exists())


# --------------------------------------------------------------------------- #
# List views (full page vs HTMX partial, pagination, filters)
# --------------------------------------------------------------------------- #
class ListViewTests(BaseViewTestCase):
    def test_full_page_vs_htmx_partial_templates(self):
        cases = (
            ("client_list", "client/list.html", "client/table-container.html"),
            ("contract_list", "contract/list.html", "contract/table-container.html"),
            ("payment_list", "payment/list.html", "payment/table-container.html"),
            ("teaching_list", "teaching/list.html", "teaching/table-container.html"),
            ("teaching_record_list", "teaching/record-list.html",
             "teaching/record-table-container.html"),
        )
        for name, full, partial in cases:
            with self.subTest(view=name, mode="full"):
                response = self.client.get(u(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, full)
            with self.subTest(view=name, mode="htmx"):
                response = self.client.get(u(name), **HTMX)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, partial)
                self.assertTemplateNotUsed(response, full)

    def test_list_contexts_include_forms_and_page_range(self):
        for name in ("client_list", "contract_list", "payment_list", "teaching_list"):
            with self.subTest(view=name):
                context = self.client.get(u(name)).context
                self.assertIn("form", context)
                self.assertEqual(list(context["custom_page_range"]), [1])

    def test_pagination_splits_at_20_items(self):
        for _ in range(19):  # base fixture has 2 contracts -> 21 total
            Contract.objects.create(client=self.client_a, total_biaya=1)

        page1 = self.client.get(u("contract_list"))
        page2 = self.client.get(u("contract_list"), {"page": 2})

        self.assertEqual(len(page1.context["contracts"]), 20)
        self.assertEqual(len(page2.context["contracts"]), 1)
        self.assertEqual(list(page1.context["custom_page_range"]), [1, 2])

    def test_page_out_of_range_returns_404(self):
        self.assertEqual(self.client.get(u("client_list"), {"page": 99}).status_code, 404)

    def test_contract_list_filters(self):
        lunas_habis = Contract.objects.create(
            client=self.client_b, total_biaya=1, pembayaran="Lunas",
            contract_status="Habis",
        )
        lunas_running = Contract.objects.create(
            client=self.client_b, total_biaya=1, pembayaran="Lunas",
        )

        def ids(**params):
            return pks(self.client.get(u("contract_list"), params), "contracts")

        self.assertEqual(ids(pembayaran="Lunas"), {lunas_habis.pk, lunas_running.pk})
        self.assertEqual(ids(contract_status="Habis"), {lunas_habis.pk})
        self.assertEqual(
            ids(pembayaran="Lunas", contract_status="Berjalan"), {lunas_running.pk}
        )
        self.assertEqual(ids(pembayaran="Nope"), set())
        # Whitespace is stripped
        self.assertEqual(ids(pembayaran=" Lunas "), {lunas_habis.pk, lunas_running.pk})

    def test_contract_list_exposes_current_filters_in_context(self):
        context = self.client.get(
            u("contract_list"), {"pembayaran": " Lunas ", "contract_status": "Habis"}
        ).context
        self.assertEqual(context["current_pembayaran"], "Lunas")
        self.assertEqual(context["current_contract_status"], "Habis")


# --------------------------------------------------------------------------- #
# Search views
# --------------------------------------------------------------------------- #
class SearchClientViewTests(BaseViewTestCase):
    def search(self, q):
        return pks(self.client.get(u("search_client"), {"search": q}, **HTMX), "clients")

    def test_empty_query_returns_all(self):
        self.assertEqual(self.search(""), {self.client_a.pk, self.client_b.pk})

    def test_whitespace_only_query_returns_all(self):
        self.assertEqual(self.search("   "), {self.client_a.pk, self.client_b.pk})

    def test_matches_name_case_insensitively(self):
        self.assertEqual(self.search("BUDI"), {self.client_a.pk})

    def test_matches_address(self):
        self.assertEqual(self.search("kenanga"), {self.client_b.pk})

    def test_kontak_requires_exact_match(self):
        self.assertEqual(self.search("0811"), {self.client_a.pk})
        self.assertEqual(self.search("081"), set())

    def test_no_match(self):
        self.assertEqual(self.search("zzz"), set())


class SearchContractViewTests(BaseViewTestCase):
    def search(self, q):
        return pks(self.client.get(u("search_contract"), {"search": q}, **HTMX), "contracts")

    def test_empty_returns_all(self):
        self.assertEqual(self.search(""), {self.contract_a.pk, self.contract_b.pk})

    def test_matches_client_name(self):
        self.assertEqual(self.search("siti"), {self.contract_b.pk})

    def test_no_match(self):
        self.assertEqual(self.search("zzz"), set())


class SearchPaymentViewTests(BaseViewTestCase):
    def search(self, q):
        return pks(self.client.get(u("search_payment"), {"search": q}, **HTMX), "payments")

    def test_empty_returns_all(self):
        self.assertEqual(self.search(""), {self.p_mar.pk, self.p_may.pk})

    def test_matches_client_name(self):
        self.assertEqual(self.search("budi"), {self.p_mar.pk})

    def test_matches_payment_code(self):
        self.assertEqual(
            self.search(self.p_may.kode_payment.lower()), {self.p_may.pk}
        )

    def test_month_filter(self):
        self.assertEqual(self.search("::3"), {self.p_mar.pk})
        self.assertEqual(self.search("::5"), {self.p_may.pk})

    def test_month_filter_accepts_leading_zero_and_spaces(self):
        self.assertEqual(self.search("::03"), {self.p_mar.pk})
        self.assertEqual(self.search("::  5 "), {self.p_may.pk})

    def test_month_filter_with_no_payments_in_month(self):
        self.assertEqual(self.search("::7"), set())

    def test_invalid_month_returns_empty_instead_of_error(self):
        for q in ("::0", "::13", "::abc", "::", "::-1"):
            with self.subTest(query=q):
                self.assertEqual(self.search(q), set())


class SearchTeachingViewTests(BaseViewTestCase):
    def search(self, q):
        return pks(self.client.get(u("search_teaching"), {"search": q}, **HTMX), "teachings")

    def test_empty_returns_all(self):
        self.assertEqual(
            self.search(""), {self.t_mon.pk, self.t_wed.pk, self.t_fri.pk}
        )

    def test_matches_client_name_without_duplicates(self):
        response = self.client.get(u("search_teaching"), {"search": "budi"}, **HTMX)
        results = list(response.context["teachings"])
        self.assertEqual({t.pk for t in results}, {self.t_mon.pk, self.t_fri.pk})
        self.assertEqual(len(results), 2)

    def test_matches_client_phone_and_contract_code(self):
        self.assertEqual(self.search("0899"), {self.t_wed.pk})
        self.assertEqual(self.search("aaaa"), {self.t_mon.pk, self.t_fri.pk})

    def test_day_names_indonesian_and_english_case_insensitive(self):
        self.assertEqual(self.search("senin"), {self.t_mon.pk})
        self.assertEqual(self.search("Rabu"), {self.t_wed.pk})
        self.assertEqual(self.search("FRIDAY"), {self.t_fri.pk})

    def test_day_number(self):
        self.assertEqual(self.search("2"), {self.t_wed.pk})

    def test_out_of_range_number_matches_nothing(self):
        self.assertEqual(self.search("9"), set())

    def test_hour_filter(self):
        self.assertEqual(self.search("::jam=14"), {self.t_wed.pk, self.t_fri.pk})
        self.assertEqual(self.search("::jam=10"), {self.t_mon.pk})
        self.assertEqual(self.search("::JAM=10"), {self.t_mon.pk})

    def test_hour_filter_invalid_values_return_empty(self):
        for q in ("::jam=abc", "::jam=", "::jam=24", "::jam=-1"):
            with self.subTest(query=q):
                self.assertEqual(self.search(q), set())


class SearchTeachingRecordViewTests(BaseViewTestCase):
    def search(self, q):
        response = self.client.get(
            u("search_teaching_record"), {"search": q}, **HTMX
        )
        return pks(response, "teaching_records")

    def test_empty_returns_all(self):
        self.assertEqual(
            self.search(""), {self.r_mon.pk, self.r_tue.pk, self.r_resched.pk}
        )

    def test_matches_client_and_contract_code(self):
        self.assertEqual(self.search("budi"), {self.r_mon.pk, self.r_resched.pk})
        self.assertEqual(self.search("bbbb"), {self.r_tue.pk})

    def test_plain_day_name_filters_by_execution_date_not_schedule(self):
        # r_resched belongs to a Monday slot but was held on a Wednesday.
        self.assertEqual(self.search("senin"), {self.r_mon.pk})
        self.assertEqual(self.search("selasa"), {self.r_tue.pk})
        self.assertEqual(self.search("rabu"), {self.r_resched.pk})

    def test_plain_day_number_uses_execution_date(self):
        # 0 = Monday ... so 2 = Wednesday (iso_week_day offset handled)
        self.assertEqual(self.search("2"), {self.r_resched.pk})

    def test_jadwal_filters_by_scheduled_day(self):
        self.assertEqual(self.search("::jadwal=senin"), {self.r_mon.pk, self.r_resched.pk})
        self.assertEqual(self.search("::jadwal=wednesday"), {self.r_tue.pk})
        self.assertEqual(self.search("::jadwal=2"), {self.r_tue.pk})

    def test_jadwal_invalid_returns_empty(self):
        for q in ("::jadwal=", "::jadwal=xyz", "::jadwal=9", "::jadwal=7"):
            with self.subTest(query=q):
                self.assertEqual(self.search(q), set())

    def test_hour_filter_uses_schedule_start_time(self):
        self.assertEqual(self.search("::jam=14"), {self.r_tue.pk})
        self.assertEqual(self.search("::jam=10"), {self.r_mon.pk, self.r_resched.pk})

    def test_hour_filter_invalid_returns_empty(self):
        for q in ("::jam=x", "::jam=99", "::jam=-1", "::jam="):
            with self.subTest(query=q):
                self.assertEqual(self.search(q), set())


# --------------------------------------------------------------------------- #
# Delete views
# --------------------------------------------------------------------------- #
class DeleteViewTests(BaseViewTestCase):
    def cases(self):
        # (url name, instance, model, trigger key, list url name)
        return (
            ("client_delete", self.client_a, Client, "clientListChanged", "client_list"),
            ("contract_delete", self.contract_a, Contract, "contractListChanged", "contract_list"),
            ("payment_delete", self.p_mar, Payment, "paymentListChanged", "payment_list"),
            ("teaching_delete", self.t_mon, Teaching, "teachingListChanged", "teaching_list"),
        )

    def test_htmx_delete_removes_object_and_sends_triggers(self):
        for name, obj, model, key, _ in self.cases():
            with self.subTest(view=name):
                response = self.client.delete(u(name, pk=obj.pk), **HTMX)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                payload = hx_trigger(response)
                self.assertIn(key, payload)
                self.assertEqual(payload["showToast"]["type"], "alert-warning")
                self.assertFalse(model.objects.filter(pk=obj.pk).exists())

    def test_non_htmx_delete_redirects_to_list(self):
        for name, obj, model, _, list_name in self.cases():
            with self.subTest(view=name):
                response = self.client.delete(u(name, pk=obj.pk))
                # self.assertRedirects(
                #     response, u(list_name), fetch_redirect_response=False
                # )
                self.assertRedirects(
                    response, u(list_name), status_code=400, fetch_redirect_response=True
                )
                self.assertFalse(model.objects.filter(pk=obj.pk).exists())

    def test_delete_unknown_pk_returns_404(self):
        for name, *_ in self.cases():
            with self.subTest(view=name):
                self.assertEqual(
                    self.client.delete(u(name, pk=999_999), **HTMX).status_code, 404
                )

    def test_deleting_client_also_removes_login_account(self):
        user_id = self.client_a.account_client_id
        self.client.delete(u("client_delete", pk=self.client_a.pk), **HTMX)
        self.assertFalse(User.objects.filter(pk=user_id).exists())


class DeleteTeachingRecordViewTests(BaseViewTestCase):
    def test_htmx_delete_sends_triggers(self):
        response = self.client.delete(
            u("teaching_record_delete", pk=self.r_mon.pk), **HTMX
        )
        self.assertEqual(response.status_code, 200)
        payload = hx_trigger(response)
        self.assertIn("RecordTeachingListChanged", payload)
        self.assertEqual(payload["showToast"]["type"], "alert-warning")
        self.assertFalse(TeachingRecord.objects.filter(pk=self.r_mon.pk).exists())

    def test_delete_reopens_habis_privat_contract(self):
        # contract_a has exactly 2 records in the fixture; make quota = 2 and exhausted.
        Contract.objects.filter(pk=self.contract_a.pk).update(
            total_pertemuan=2, contract_status="Habis"
        )
        self.client.delete(u("teaching_record_delete", pk=self.r_mon.pk), **HTMX)
        self.contract_a.refresh_from_db()
        self.assertEqual(self.contract_a.contract_status, "Berjalan")

    def test_delete_keeps_other_records(self):
        self.client.delete(u("teaching_record_delete", pk=self.r_mon.pk), **HTMX)
        self.assertTrue(TeachingRecord.objects.filter(pk=self.r_tue.pk).exists())


# --------------------------------------------------------------------------- #
# Create / Edit views - ModelForm validation is mocked (forms.py not provided),
# so these tests exercise only the view's own HTMX response logic.
# --------------------------------------------------------------------------- #
class CreateViewTests(BaseViewTestCase):
    CASES = (
        # url name, form class attr in views, trigger key, template, retarget
        ("client_create", "ClientForm", "clientListChanged",
         "client/form-fields.html", "#add-client-form"),
        ("contract_create", "ContractForm", "contractListChanged",
         "contract/form-fields.html", "#add-contract-form"),
        ("payment_create", "PaymentForm", "paymentListChanged",
         "payment/form-fields.html", "#add-payment-form"),
        ("teaching_create", "TeachingForm", "teachingListChanged",
         "teaching/form-fields.html", "#add-teach-form"),
    )

    def test_valid_form_saves_and_triggers_list_refresh(self):
        for name, form_attr, key, _, _ in self.CASES:
            form_cls = getattr(views, form_attr)
            with self.subTest(view=name), \
                    mock.patch.object(form_cls, "is_valid", return_value=True), \
                    mock.patch.object(form_cls, "save") as save:
                response = self.client.post(u(name), {}, **HTMX)
                self.assertEqual(response.status_code, 200)
                save.assert_called_once()
                payload = hx_trigger(response)
                self.assertIn(key, payload)
                self.assertEqual(payload["showToast"]["type"], "alert-success")

    def test_invalid_form_rerenders_and_retargets(self):
        for name, form_attr, _, template, target in self.CASES:
            form_cls = getattr(views, form_attr)
            with self.subTest(view=name), \
                    mock.patch.object(form_cls, "is_valid", return_value=False), \
                    mock.patch.object(form_cls, "save") as save:
                response = self.client.post(u(name), {}, **HTMX)
                self.assertEqual(response.status_code, 200)
                save.assert_not_called()
                self.assertTemplateUsed(response, template)
                self.assertEqual(response["HX-Retarget"], target)
                self.assertEqual(response["HX-Reswap"], "outerHTML")
                self.assertEqual(toast(response)["type"], "alert-error")

    def test_client_create_returns_fresh_form_after_success(self):
        with mock.patch.object(views.ClientForm, "is_valid", return_value=True), \
                mock.patch.object(views.ClientForm, "save"):
            response = self.client.post(u("client_create"), {}, **HTMX)
        self.assertTemplateUsed(response, "client/form-fields.html")


class EditViewTests(BaseViewTestCase):
    def cases(self):
        return (
            ("client_edit", self.client_a, "ClientForm", "clientListChanged",
             "edit-client-form"),
            ("contract_edit", self.contract_a, "ContractUpdateForm", "contractListChanged",
             "edit-contract-form"),
            ("payment_edit", self.p_mar, "PaymentUpdateForm", "paymentListChanged",
             "edit-payment-form"),
            ("teaching_edit", self.t_mon, "TeachingUpdateForm", "teachingListChanged",
             "edit-teach-form"),
        )

    def test_valid_form_returns_empty_response_with_triggers(self):
        for name, obj, form_attr, key, _ in self.cases():
            form_cls = getattr(views, form_attr)
            with self.subTest(view=name), \
                    mock.patch.object(form_cls, "is_valid", return_value=True), \
                    mock.patch.object(form_cls, "save"):
                response = self.client.post(u(name, pk=obj.pk), {}, **HTMX)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                payload = hx_trigger(response)
                self.assertIn(key, payload)
                self.assertEqual(payload["showToast"]["type"], "alert-success")

    def test_invalid_form_retargets_to_object_specific_form(self):
        for name, obj, form_attr, _, dom_prefix in self.cases():
            form_cls = getattr(views, form_attr)
            with self.subTest(view=name), \
                    mock.patch.object(form_cls, "is_valid", return_value=False):
                response = self.client.post(u(name, pk=obj.pk), {}, **HTMX)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["HX-Retarget"], f"#{dom_prefix}-{obj.pk}")
                self.assertEqual(response["HX-Reswap"], "outerHTML")
                self.assertEqual(toast(response)["type"], "alert-error")

    def test_unknown_pk_returns_404(self):
        for name, *_ in self.cases():
            with self.subTest(view=name):
                self.assertEqual(
                    self.client.get(u(name, pk=999_999), **HTMX).status_code, 404
                )


# --------------------------------------------------------------------------- #
# RecordTeachingView - core business flow for logging a teaching session
# --------------------------------------------------------------------------- #
class RecordTeachingViewTests(BaseViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.privat = Contract.objects.create(
            client=cls.client_a, total_biaya=1, total_pertemuan=3, kode_kontrak="PRIV"
        )
        cls.t_privat = Teaching.objects.create(
            client=cls.client_a, kontrak=cls.privat, day_of_week=5,
            start_time=time(9, 0), end_time=time(10, 0), materi="Kanji dasar",
        )
        cls.institusi = Contract.objects.create(
            client=cls.client_b, total_biaya=1, tipe_kontrak="Institusi",
            kode_kontrak="INST",
        )
        cls.t_inst = Teaching.objects.create(
            client=cls.client_b, kontrak=cls.institusi, day_of_week=5,
            start_time=time(11, 0), end_time=time(12, 0), materi="Percakapan",
        )

    def post(self, teaching, **data):
        return self.client.post(u("teaching_record", pk=teaching.pk), data)

    def records(self, contract):
        return TeachingRecord.objects.filter(kontrak=contract)

    # --- GET ------------------------------------------------------------- #
    def test_get_renders_modal_with_context(self):
        response = self.client.get(u("teaching_record", pk=self.t_privat.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teaching/record-modal.html")
        self.assertEqual(response.context["teaching"], self.t_privat)
        self.assertRegex(
            response.context["now_iso"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"
        )
        self.assertIn("custom_page_range", response.context)

    def test_get_unknown_teaching_returns_404(self):
        self.assertEqual(self.client.get(u("teaching_record", pk=999_999)).status_code, 404)

    def test_post_unknown_teaching_returns_404(self):
        self.assertEqual(self.client.post(u("teaching_record", pk=999_999), {}).status_code, 404)

    def test_requires_login(self):
        self.client.logout()
        response = self.post(self.t_privat)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.records(self.privat).count(), 0)

    # --- Privat: success paths ------------------------------------------ #
    def test_privat_success_creates_record(self):
        response = self.post(
            self.t_privat,
            materi_realisasi="Katakana",
            is_rescheduled="on",
            tanggal_pelaksanaan="2025-01-06T10:30",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        payload = hx_trigger(response)
        self.assertIn("teachingListChanged", payload)
        self.assertEqual(payload["showToast"]["type"], "alert-success")
        self.assertIn("Privat", payload["showToast"]["message"])

        record = self.records(self.privat).get()
        self.assertEqual(record.teaching, self.t_privat)
        self.assertEqual(record.materi_realisasi, "Katakana")
        self.assertTrue(record.is_rescheduled)
        self.assertEqual(record.tanggal_pelaksanaan, aware(2025, 1, 6, 10, 30))

    def test_materi_defaults_to_teaching_materi_when_field_missing(self):
        self.post(self.t_privat)
        self.assertEqual(self.records(self.privat).get().materi_realisasi, "Kanji dasar")

    def test_explicit_empty_materi_is_respected(self):
        self.post(self.t_privat, materi_realisasi="")
        self.assertEqual(self.records(self.privat).get().materi_realisasi, "")

    def test_is_rescheduled_only_true_for_on(self):
        self.post(self.t_privat)
        self.post(self.t_privat, is_rescheduled="true")
        self.post(self.t_privat, is_rescheduled="on")
        flags = sorted(self.records(self.privat).values_list("is_rescheduled", flat=True))
        self.assertEqual(flags, [False, False, True])

    def test_blank_date_uses_current_time(self):
        fixed = aware(2020, 2, 3, 8, 0)
        with mock.patch("django.utils.timezone.now", return_value=fixed):
            self.post(self.t_privat, tanggal_pelaksanaan="")
        self.assertEqual(self.records(self.privat).get().tanggal_pelaksanaan, fixed)

    # --- Date validation ------------------------------------------------- #
    def test_invalid_date_format_is_rejected(self):
        for bad in ("not-a-date", "06/01/2025 10:00", "2025-13-45T99:99"):
            with self.subTest(value=bad):
                response = self.post(self.t_privat, tanggal_pelaksanaan=bad)
                self.assertEqual(toast(response)["type"], "alert-error")
                self.assertIn("tidak valid", toast(response)["message"])
        self.assertEqual(self.records(self.privat).count(), 0)

    def test_timezone_aware_date_string_is_rejected_not_500(self):
        response = self.post(self.t_privat, tanggal_pelaksanaan="2025-01-06T10:30+07:00")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(toast(response)["type"], "alert-error")
        self.assertEqual(self.records(self.privat).count(), 0)

    # --- Contract state rules ------------------------------------------- #
    def test_finished_contract_is_rejected(self):
        Contract.objects.filter(pk=self.privat.pk).update(contract_status="Habis")
        response = self.post(self.t_privat)
        self.assertEqual(toast(response)["type"], "alert-error")
        self.assertIn("selesai", toast(response)["message"])
        self.assertEqual(self.records(self.privat).count(), 0)

    def test_privat_quota_already_met_is_rejected_with_warning(self):
        # Inconsistent-but-possible state: quota reached, status still Berjalan.
        for _ in range(3):
            TeachingRecord.objects.create(kontrak=self.privat, teaching=self.t_privat)
        response = self.post(self.t_privat)
        self.assertEqual(toast(response)["type"], "alert-warning")
        self.assertNotIn("teachingListChanged", hx_trigger(response))
        self.assertEqual(self.records(self.privat).count(), 3)

    def test_last_privat_session_flips_contract_to_habis(self):
        for _ in range(2):
            TeachingRecord.objects.create(kontrak=self.privat, teaching=self.t_privat)

        response = self.post(self.t_privat)

        self.assertEqual(toast(response)["type"], "alert-success")
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Habis")
        self.assertEqual(self.records(self.privat).count(), 3)

        # ...and the next attempt is blocked.
        again = self.post(self.t_privat)
        self.assertEqual(toast(again)["type"], "alert-error")
        self.assertEqual(self.records(self.privat).count(), 3)

    def test_privat_without_quota_is_unlimited_and_never_habis(self):
        Contract.objects.filter(pk=self.privat.pk).update(total_pertemuan=0)
        for _ in range(5):
            self.post(self.t_privat)
        self.privat.refresh_from_db()
        self.assertEqual(self.records(self.privat).count(), 5)
        self.assertEqual(self.privat.contract_status, "Berjalan")

    # --- Institusi ------------------------------------------------------- #
    def test_institusi_success_has_no_quota_and_stays_berjalan(self):
        for _ in range(4):
            response = self.post(self.t_inst)
        self.assertEqual(toast(response)["type"], "alert-success")
        self.assertIn("Institusi", toast(response)["message"])
        self.assertIn("teachingListChanged", hx_trigger(response))
        self.assertEqual(self.records(self.institusi).count(), 4)
        self.institusi.refresh_from_db()
        self.assertEqual(self.institusi.contract_status, "Berjalan")

    def test_unknown_contract_type_is_rejected(self):
        Contract.objects.filter(pk=self.institusi.pk).update(tipe_kontrak="Lainnya")
        response = self.post(self.t_inst)
        self.assertEqual(toast(response)["type"], "alert-error")
        self.assertIn("tidak dikenali", toast(response)["message"])
        self.assertEqual(self.records(self.institusi).count(), 0)


# --------------------------------------------------------------------------- #
# django-autocomplete-light views (called directly; no URL names needed)
# --------------------------------------------------------------------------- #
class AutocompleteViewTests(BaseViewTestCase):
    def make_view(self, view_cls, user=None, q="", forwarded=None):
        request = RequestFactory().get("/autocomplete/")
        request.user = user if user is not None else self.user
        view = view_cls()
        view.request = request
        view.q = q
        view.forwarded = forwarded or {}
        return view

    # --- Client ---------------------------------------------------------- #
    def test_client_autocomplete_empty_for_anonymous(self):
        view = self.make_view(views.ClientFormAutocomplete, user=AnonymousUser())
        self.assertEqual(view.get_queryset().count(), 0)

    def test_client_autocomplete_returns_all_without_query(self):
        view = self.make_view(views.ClientFormAutocomplete)
        self.assertEqual(
            set(view.get_queryset()), {self.client_a, self.client_b}
        )

    def test_client_autocomplete_matches_name_address_and_exact_phone(self):
        for q, expected in (
            ("budi", self.client_a),
            ("kenanga", self.client_b),
            ("0899", self.client_b),
        ):
            with self.subTest(q=q):
                view = self.make_view(views.ClientFormAutocomplete, q=q)
                self.assertEqual(list(view.get_queryset()), [expected])

    def test_client_autocomplete_partial_phone_does_not_match(self):
        view = self.make_view(views.ClientFormAutocomplete, q="089")
        self.assertEqual(view.get_queryset().count(), 0)

    # --- Contract -------------------------------------------------------- #
    def test_contract_autocomplete_empty_for_anonymous(self):
        view = self.make_view(views.ContractFormAutocomplete, user=AnonymousUser())
        self.assertEqual(view.get_queryset().count(), 0)

    def test_contract_autocomplete_filters_by_forwarded_client(self):
        view = self.make_view(
            views.ContractFormAutocomplete, forwarded={"client": self.client_b.pk}
        )
        self.assertEqual(list(view.get_queryset()), [self.contract_b])

    def test_contract_autocomplete_without_forwarded_client_returns_all(self):
        view = self.make_view(views.ContractFormAutocomplete)
        self.assertEqual(
            set(view.get_queryset()), {self.contract_a, self.contract_b}
        )

    def test_contract_autocomplete_search_fields(self):
        for q, expected in (
            ("siti", self.contract_b),      # client name
            ("melati", self.contract_a),    # client address
            ("0811", self.contract_a),      # client phone (exact)
            ("bbb", self.contract_b),       # contract code
        ):
            with self.subTest(q=q):
                view = self.make_view(views.ContractFormAutocomplete, q=q)
                self.assertEqual(list(view.get_queryset()), [expected])

    def test_contract_autocomplete_combines_client_filter_and_query(self):
        view = self.make_view(
            views.ContractFormAutocomplete,
            q="siti",
            forwarded={"client": self.client_a.pk},
        )
        self.assertEqual(view.get_queryset().count(), 0)
