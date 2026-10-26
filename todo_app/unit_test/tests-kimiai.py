"""
Unit test untuk models.py, forms.py, views.py, dan urls.py pada app todo_app.

Simpan file ini sebagai todo_app/tests.py, lalu jalankan:
    python manage.py test todo_app

Test view sengaja tidak merender template HTML. Context dan nama template tetap
diperiksa, sedangkan django.shortcuts.render di-mock ketika dibutuhkan.
"""

import json
from datetime import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from todo_app.forms import (
    ClientForm,
    ContractForm,
    ContractUpdateForm,
    PaymentForm,
    PaymentUpdateForm,
    TeachingForm,
    TeachingUpdateForm,
)
from todo_app.models import (
    Client,
    Contract,
    Payment,
    Teaching,
    TeachingRecord,
    generate_unique_username,
)
from todo_app.views import (
    AboutView,
    ClientFormAutocomplete,
    ContractFormAutocomplete,
    CreateClientView,
    CreateContractView,
    CreatePaymentView,
    CreateTeachingView,
    CustomLoginView,
    DeleteClientView,
    DeleteContractView,
    DeletePaymentView,
    DeleteTeachingRecordView,
    DeleteTeachingView,
    EditClientView,
    EditContractView,
    EditPaymentView,
    EditTeachingView,
    ListClientView,
    ListContractView,
    ListPaymentView,
    ListTeachingRecordView,
    ListTeachingView,
    RecordTeachingView,
    SearchClientView,
    SearchContractView,
    SearchPaymentView,
    SearchTeachingRecordView,
    SearchTeachingView,
    logout_view,
)


User = get_user_model()
_USE_LOGGED_IN_USER = object()


def make_client(nama="Budi Santoso", kontak="081234567890", **overrides):
    data = {
        "nama": nama,
        "kontak": kontak,
        "kota": "Jakarta",
        "alamat": "Jalan Melati No. 1",
    }
    data.update(overrides)
    return Client.objects.create(**data)


def make_contract(client=None, **overrides):
    if client is None:
        client = make_client()
    data = {
        "client": client,
        "total_pertemuan": 4,
        "total_biaya": 1_000_000,
        "tipe_kontrak": "Privat",
        "pembayaran": "Kredit",
        "contract_status": "Berjalan",
        "keterangan": "Kontrak les privat",
    }
    data.update(overrides)
    return Contract.objects.create(**data)


def make_payment(contract=None, **overrides):
    if contract is None:
        contract = make_contract()
    data = {
        "contract": contract,
        "tanggal": timezone.make_aware(timezone.datetime(2026, 1, 5, 10, 0)),
        "total": 250_000,
    }
    data.update(overrides)
    return Payment.objects.create(**data)


def make_teaching(client=None, contract=None, **overrides):
    if client is None:
        client = make_client()
    if contract is None:
        contract = make_contract(client=client)
    data = {
        "client": client,
        "kontrak": contract,
        "day_of_week": 0,
        "start_time": time(8, 0),
        "end_time": time(9, 0),
        "materi": "Hiragana",
        "status_teaching": True,
    }
    data.update(overrides)
    return Teaching.objects.create(**data)


def make_record(contract=None, teaching=None, **overrides):
    if teaching is not None:
        contract = teaching.kontrak
    if contract is None:
        contract = make_contract()
    data = {
        "kontrak": contract,
        "teaching": teaching,
        "tanggal_pelaksanaan": timezone.make_aware(
            timezone.datetime(2026, 1, 5, 8, 0)
        ),
        "materi_realisasi": "Latihan membaca",
        "is_rescheduled": False,
    }
    data.update(overrides)
    return TeachingRecord.objects.create(**data)


def contract_form_data(client, **overrides):
    data = {
        "client": client.pk,
        "tipe_kontrak": "Privat",
        "total_pertemuan": 4,
        "total_biaya": 1_000_000,
        "keterangan": "Keterangan",
    }
    data.update(overrides)
    return data


def payment_form_data(contract, **overrides):
    data = {
        "contract": contract.pk,
        "tanggal_0": "2026-01-05",
        "tanggal_1": "10:30",
        "total": 250_000,
    }
    data.update(overrides)
    return data


def teaching_form_data(client, contract, **overrides):
    data = {
        "client": client.pk,
        "kontrak": contract.pk,
        "day_of_week": 0,
        "start_time": "08:00",
        "end_time": "09:00",
        "materi": "Hiragana",
    }
    data.update(overrides)
    return data


class UsernameGeneratorTests(TestCase):
    @patch("todo_app.models.random.randint", return_value=123)
    def test_username_removes_spaces_and_uses_random_suffix(self, _mock_randint):
        username = generate_unique_username("Budi Santoso")
        self.assertEqual(username, "BudiSantoso_123")

    @patch("todo_app.models.random.randint", side_effect=[123, 123, 124])
    def test_username_retries_when_candidate_already_exists(self, mock_randint):
        User.objects.create_user(username="Budi_123", password="secret")

        username = generate_unique_username("Budi")

        self.assertEqual(username, "Budi_124")
        self.assertEqual(mock_randint.call_count, 3)


class ClientModelTests(TestCase):
    def test_string_representation(self):
        client = make_client(nama="Siti", kontak="081111111111")
        self.assertEqual(str(client), "Siti-081111111111")

    def test_create_client_automatically_creates_usable_user_account(self):
        client = make_client(nama="Budi Santoso")

        self.assertIsNotNone(client.account_client)
        self.assertTrue(client.account_client.username.startswith("BudiSantoso_"))
        self.assertTrue(client.account_client.check_password("Alhamdulillah123"))

    def test_update_name_regenerates_related_username(self):
        client = make_client(nama="Budi")
        old_username = client.account_client.username

        client.nama = "Andi Wijaya"
        client.save()
        client.account_client.refresh_from_db()

        self.assertNotEqual(client.account_client.username, old_username)
        self.assertTrue(client.account_client.username.startswith("AndiWijaya_"))

    def test_update_without_name_change_preserves_username(self):
        client = make_client()
        original_username = client.account_client.username

        client.kota = "Bandung"
        client.save()
        client.account_client.refresh_from_db()

        self.assertEqual(client.account_client.username, original_username)
        self.assertEqual(client.kota, "Bandung")

    def test_delete_client_also_deletes_related_user(self):
        client = make_client()
        user_id = client.account_client_id

        client.delete()

        self.assertFalse(Client.objects.filter(pk=client.pk).exists())
        self.assertFalse(User.objects.filter(pk=user_id).exists())

    def test_contact_must_be_unique(self):
        make_client(kontak="080000000000")

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_client(nama="Client Lain", kontak="080000000000")


class ContractModelTests(TestCase):
    def setUp(self):
        self.client = make_client()
        self.contract = make_contract(client=self.client)

    def test_string_representation(self):
        self.assertEqual(
            str(self.contract),
            f"{self.client.nama} -- {self.contract.kode_kontrak}",
        )

    def test_contract_code_is_generated_once(self):
        original_code = self.contract.kode_kontrak
        self.assertRegex(original_code, r"^[A-Z0-9]{4}$")

        self.contract.keterangan = "Diperbarui"
        self.contract.save()

        self.assertEqual(self.contract.kode_kontrak, original_code)

    @patch("todo_app.models.get_random_string", side_effect=["aaaa", "bbbb"])
    def test_contract_code_retries_on_collision(self, mock_random_string):
        make_contract(client=self.client, kode_kontrak="AAAA")

        contract = make_contract(client=self.client)

        self.assertEqual(contract.kode_kontrak, "BBBB")
        self.assertEqual(mock_random_string.call_count, 2)

    def test_total_pembayaran_sums_all_related_payments(self):
        make_payment(contract=self.contract, total=200_000)
        make_payment(contract=self.contract, total=300_000)

        self.assertEqual(self.contract.total_pembayaran(), 500_000)

    def test_update_status_pembayaran_marks_lunas_when_paid_in_full(self):
        make_payment(contract=self.contract, total=self.contract.total_biaya)

        self.contract.update_status_pembayaran()
        self.contract.refresh_from_db()

        self.assertEqual(self.contract.pembayaran, "Lunas")

    def test_update_status_pembayaran_returns_to_kredit_when_below_total(self):
        make_payment(contract=self.contract, total=100_000)
        self.contract.pembayaran = "Lunas"
        self.contract.save(update_fields=["pembayaran"])

        self.contract.update_status_pembayaran()
        self.contract.refresh_from_db()

        self.assertEqual(self.contract.pembayaran, "Kredit")

    def test_private_progress_is_zero_without_meeting_quota(self):
        self.contract.total_pertemuan = 0
        self.assertEqual(self.contract.progress_percentage, 0)

    def test_private_progress_is_rounded_and_capped_at_one_hundred(self):
        self.contract.total_pertemuan = 3
        make_record(contract=self.contract)
        self.assertEqual(self.contract.progress_percentage, 33)

        make_record(contract=self.contract)
        make_record(contract=self.contract)
        make_record(contract=self.contract)
        self.assertEqual(self.contract.progress_percentage, 100)

    def test_institution_progress_is_always_one_hundred(self):
        institution = make_contract(client=self.client, tipe_kontrak="Institusi")
        self.assertEqual(institution.progress_percentage, 100)

    def test_check_and_update_status_finishes_private_contract_at_quota(self):
        self.contract.total_pertemuan = 1
        self.contract.save(update_fields=["total_pertemuan"])
        make_record(contract=self.contract)

        self.contract.check_and_update_status()
        self.contract.refresh_from_db()

        self.assertEqual(self.contract.contract_status, "Habis")

    def test_check_and_update_status_does_not_finish_institution_contract(self):
        institution = make_contract(
            client=self.client,
            tipe_kontrak="Institusi",
            total_pertemuan=1,
        )
        make_record(contract=institution)

        institution.check_and_update_status()
        institution.refresh_from_db()

        self.assertEqual(institution.contract_status, "Berjalan")


class PaymentModelTests(TestCase):
    def test_payment_code_and_string_representation(self):
        payment = make_payment()

        self.assertRegex(payment.kode_payment, r"^PAY-[A-Z0-9]{4}$")
        self.assertEqual(
            str(payment),
            f"{payment.contract.client.nama} -- {payment.kode_payment}",
        )

    @patch("todo_app.models.get_random_string", side_effect=["aaaa", "bbbb"])
    def test_payment_code_retries_on_collision(self, mock_random_string):
        contract = make_contract()
        make_payment(contract=contract, kode_payment="PAY-AAAA")

        payment = make_payment(contract=contract)

        self.assertEqual(payment.kode_payment, "PAY-BBBB")
        self.assertEqual(mock_random_string.call_count, 2)


class TeachingModelTests(TestCase):
    def setUp(self):
        self.client = make_client()
        self.contract = make_contract(client=self.client)

    def test_clean_accepts_valid_schedule(self):
        teaching = Teaching(
            client=self.client,
            kontrak=self.contract,
            day_of_week=0,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        teaching.full_clean()
        self.assertEqual(teaching.total_mengajar, 0)

    def test_clean_rejects_contract_from_another_client(self):
        other_client = make_client(nama="Client Lain", kontak="089999999999")
        other_contract = make_contract(client=other_client)
        teaching = Teaching(
            client=self.client,
            kontrak=other_contract,
            day_of_week=0,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(ValidationError) as context:
            teaching.full_clean()

        self.assertIn("kontrak", context.exception.error_dict)

    def test_clean_rejects_end_time_not_after_start_time(self):
        teaching = Teaching(
            client=self.client,
            kontrak=self.contract,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(ValidationError) as context:
            teaching.full_clean()

        self.assertIn("end_time", context.exception.error_dict)

    def test_clean_rejects_overlapping_schedule(self):
        make_teaching(
            client=self.client,
            contract=self.contract,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        overlapping = Teaching(
            client=self.client,
            kontrak=self.contract,
            day_of_week=0,
            start_time=time(8, 30),
            end_time=time(9, 30),
        )

        with self.assertRaises(ValidationError) as context:
            overlapping.full_clean()

        self.assertIn("start_time", context.exception.error_dict)
        self.assertIn("end_time", context.exception.error_dict)

    def test_clean_allows_back_to_back_schedule(self):
        make_teaching(
            client=self.client,
            contract=self.contract,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        adjacent = Teaching(
            client=self.client,
            kontrak=self.contract,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        adjacent.full_clean()
        self.assertTrue(adjacent.status_teaching)

    def test_clean_excludes_current_instance_when_updating(self):
        teaching = make_teaching(client=self.client, contract=self.contract)
        teaching.start_time = time(8, 30)
        teaching.end_time = time(9, 30)

        teaching.full_clean()
        self.assertEqual(teaching.start_time, time(8, 30))

    def test_progress_properties_delegate_to_contract(self):
        teaching = make_teaching(client=self.client, contract=self.contract)
        make_record(contract=self.contract, teaching=teaching)

        self.assertEqual(teaching.total_mengajar, 1)
        self.assertEqual(teaching.progress_percentage, 25)


class TeachingRecordModelTests(TestCase):
    def test_delete_reopens_finished_private_contract_below_quota(self):
        teaching = make_teaching()
        teaching.kontrak.total_pertemuan = 1
        teaching.kontrak.contract_status = "Habis"
        teaching.kontrak.save(update_fields=["total_pertemuan", "contract_status"])
        record = make_record(teaching=teaching)

        record.delete()
        teaching.kontrak.refresh_from_db()

        self.assertEqual(teaching.kontrak.contract_status, "Berjalan")

    def test_delete_does_not_change_institution_contract_status(self):
        institution = make_contract(
            tipe_kontrak="Institusi",
            total_pertemuan=1,
            contract_status="Habis",
        )
        record = make_record(contract=institution)

        record.delete()
        institution.refresh_from_db()

        self.assertEqual(institution.contract_status, "Habis")

    def test_string_representation_contains_client_and_execution_date(self):
        record = make_record()
        expected = (
            f"{record.kontrak.client.nama} - "
            f"{record.tanggal_pelaksanaan.strftime('%d/%m/%Y %H:%M')}"
        )
        self.assertEqual(str(record), expected)


class FormTests(TestCase):
    def setUp(self):
        self.client = make_client()
        self.contract = make_contract(client=self.client)

    def test_client_form_accepts_valid_data(self):
        form = ClientForm(
            data={
                "nama": "Client Baru",
                "kontak": "081200000001",
                "kota": "Depok",
                "alamat": "Jalan Baru",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_client_form_requires_name_and_contact(self):
        form = ClientForm(data={"nama": "", "kontak": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("nama", form.errors)
        self.assertIn("kontak", form.errors)

    def test_client_form_rejects_duplicate_contact(self):
        form = ClientForm(
            data={
                "nama": "Client Duplikat",
                "kontak": self.client.kontak,
                "kota": "Jakarta",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("kontak", form.errors)

    def test_contract_form_accepts_valid_data_and_sets_dropdown_parent(self):
        form = ContractForm(data=contract_form_data(self.client))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.fields["client"].widget.attrs["data-dropdown-parent"],
            "#add-contract-modal",
        )

    def test_contract_form_rejects_negative_total_cost(self):
        form = ContractForm(data=contract_form_data(self.client, total_biaya=-1))
        self.assertFalse(form.is_valid())
        self.assertIn("total_biaya", form.errors)

    def test_contract_update_form_contains_status_fields(self):
        form = ContractUpdateForm(
            data=contract_form_data(
                self.client,
                pembayaran="Lunas",
                contract_status="Habis",
            )
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn("pembayaran", form.fields)
        self.assertIn("contract_status", form.fields)
        self.assertEqual(
            form.fields["client"].widget.attrs["data-dropdown-parent"],
            "#edit-contract-modal",
        )

    def test_payment_form_parses_split_date_and_time(self):
        form = PaymentForm(data=payment_form_data(self.contract))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["tanggal"].hour, 10)
        self.assertEqual(form.cleaned_data["tanggal"].minute, 30)
        self.assertEqual(
            form.fields["contract"].widget.attrs["data-dropdown-parent"],
            "#add-payment-modal",
        )

    def test_payment_form_requires_both_date_and_time(self):
        form = PaymentForm(data=payment_form_data(self.contract, tanggal_1=""))
        self.assertFalse(form.is_valid())
        self.assertIn("tanggal", form.errors)

    def test_payment_update_form_uses_edit_dropdown_parent(self):
        form = PaymentUpdateForm(data=payment_form_data(self.contract))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.fields["contract"].widget.attrs["data-dropdown-parent"],
            "#edit-payment-modal",
        )

    def test_teaching_form_accepts_valid_data(self):
        form = TeachingForm(data=teaching_form_data(self.client, self.contract))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.fields["kontrak"].widget.attrs["data-dropdown-parent"],
            "#add-teach-modal",
        )

    def test_teaching_form_runs_model_validation(self):
        form = TeachingForm(
            data=teaching_form_data(
                self.client,
                self.contract,
                start_time="10:00",
                end_time="09:00",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)

    def test_teaching_update_form_contains_status_and_edit_dropdown_parent(self):
        form = TeachingUpdateForm(
            data=teaching_form_data(
                self.client,
                self.contract,
                status_teaching="on",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn("status_teaching", form.fields)
        self.assertEqual(
            form.fields["client"].widget.attrs["data-dropdown-parent"],
            "#edit-teach-modal",
        )


class AboutViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_view(self, query=""):
        view = AboutView()
        view.request = self.factory.get("/about-me/", data=query)
        return view

    def test_default_template_and_context(self):
        view = self.get_view()
        context = view.get_context_data()

        self.assertEqual(view.get_template_names(), ["about_sakura.html"])
        self.assertEqual(context["style"], "sakura")
        self.assertIn("profile", context)
        self.assertTrue(context["wa_url"].startswith("https://wa.me/"))
        self.assertIn("text=", context["wa_url"])

    def test_valid_style_selects_matching_template(self):
        for style, template in AboutView.TEMPLATES.items():
            with self.subTest(style=style):
                view = self.get_view({"style": style})
                self.assertEqual(view.get_template_names(), [template])
                self.assertEqual(view.get_context_data()["style"], style)

    def test_unknown_style_falls_back_to_default(self):
        view = self.get_view({"style": "unknown"})
        self.assertEqual(view.get_template_names(), ["about_sakura.html"])
        self.assertEqual(view.get_context_data()["style"], "sakura")


class AutocompleteTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="admin", password="secret")
        self.budi = make_client(nama="Budi", kontak="081111111111", alamat="Bandung")
        self.siti = make_client(nama="Siti", kontak="082222222222", alamat="Jakarta")
        self.budi_contract = make_contract(client=self.budi)
        self.siti_contract = make_contract(client=self.siti)

    def client_view(self, query="", authenticated=True):
        view = ClientFormAutocomplete()
        view.request = self.factory.get("/client-autocomplete/")
        view.request.user = self.user if authenticated else AnonymousUser()
        view.q = query
        return view

    def contract_view(self, query="", client_id=None, authenticated=True):
        view = ContractFormAutocomplete()
        view.request = self.factory.get("/contract-autocomplete/")
        view.request.user = self.user if authenticated else AnonymousUser()
        view.q = query
        view.forwarded = {"client": client_id} if client_id else {}
        return view

    def test_client_autocomplete_is_empty_for_anonymous_user(self):
        self.assertEqual(self.client_view(authenticated=False).get_queryset().count(), 0)

    def test_client_autocomplete_searches_name_address_and_exact_contact(self):
        self.assertEqual(list(self.client_view("budi").get_queryset()), [self.budi])
        self.assertEqual(list(self.client_view("jakarta").get_queryset()), [self.siti])
        self.assertEqual(
            list(self.client_view("081111111111").get_queryset()),
            [self.budi],
        )

    def test_contract_autocomplete_is_empty_for_anonymous_user(self):
        self.assertEqual(self.contract_view(authenticated=False).get_queryset().count(), 0)

    def test_contract_autocomplete_filters_forwarded_client(self):
        queryset = self.contract_view(client_id=self.budi.pk).get_queryset()
        self.assertEqual(list(queryset), [self.budi_contract])

    def test_contract_autocomplete_searches_contract_code(self):
        queryset = self.contract_view(
            query=self.siti_contract.kode_kontrak
        ).get_queryset()
        self.assertEqual(list(queryset), [self.siti_contract])


class AuthenticatedViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="admin", password="secret")

    def request(
        self,
        method="get",
        path="/",
        data=None,
        htmx=False,
        user=_USE_LOGGED_IN_USER,
    ):
        headers = {"HTTP_HX_REQUEST": "true"} if htmx else {}
        request = getattr(self.factory, method)(path, data=data or {}, **headers)
        request.user = self.user if user is _USE_LOGGED_IN_USER else user
        return request

    def assert_hx_event(self, response, event_name):
        payload = json.loads(response["HX-Trigger"])
        self.assertIn(event_name, payload)
        return payload


class AuthenticationAndRequestGuardTests(AuthenticatedViewTestCase):
    def test_protected_class_views_redirect_anonymous_users(self):
        cases = [
            (ListClientView, {}),
            (CreateClientView, {}),
            (EditClientView, {"pk": 1}),
            (DeleteClientView, {"pk": 1}),
            (SearchClientView, {}),
            (ListContractView, {}),
            (CreateContractView, {}),
            (EditContractView, {"pk": 1}),
            (DeleteContractView, {"pk": 1}),
            (SearchContractView, {}),
            (ListPaymentView, {}),
            (CreatePaymentView, {}),
            (EditPaymentView, {"pk": 1}),
            (DeletePaymentView, {"pk": 1}),
            (SearchPaymentView, {}),
            (ListTeachingView, {}),
            (CreateTeachingView, {}),
            (EditTeachingView, {"pk": 1}),
            (DeleteTeachingView, {"pk": 1}),
            (SearchTeachingView, {}),
            (RecordTeachingView, {"pk": 1}),
            (ListTeachingRecordView, {}),
            (DeleteTeachingRecordView, {"pk": 1}),
            (SearchTeachingRecordView, {}),
        ]

        for view_class, kwargs in cases:
            with self.subTest(view=view_class.__name__):
                request = self.request(user=AnonymousUser(), htmx=True)
                response = view_class.as_view()(request, **kwargs)
                self.assertEqual(response.status_code, 302)
                self.assertIn("next=", response.url)

    def test_custom_login_success_url_targets_teaching_list(self):
        self.assertEqual(
            str(CustomLoginView().get_success_url()),
            reverse("todo_app:teaching_list"),
        )

    def test_logout_clears_session_and_redirects_to_login(self):
        request = self.request(path="/logout/")
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session.save()

        response = logout_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("todo_app:login"))
        self.assertFalse(request.user.is_authenticated)

    def test_create_and_edit_views_reject_non_htmx_requests(self):
        cases = [
            (CreateClientView, {}),
            (EditClientView, {"pk": 1}),
            (CreateContractView, {}),
            (EditContractView, {"pk": 1}),
            (CreatePaymentView, {}),
            (EditPaymentView, {"pk": 1}),
            (CreateTeachingView, {}),
            (EditTeachingView, {"pk": 1}),
        ]
        for view_class, kwargs in cases:
            with self.subTest(view=view_class.__name__):
                response = view_class.as_view()(self.request(), **kwargs)
                self.assertEqual(response.status_code, 400)

    def test_search_views_return_404_for_non_htmx_requests(self):
        views = [
            SearchClientView,
            SearchContractView,
            SearchPaymentView,
            SearchTeachingView,
            SearchTeachingRecordView,
        ]
        for view_class in views:
            with self.subTest(view=view_class.__name__):
                with self.assertRaises(Http404):
                    view_class.as_view()(self.request())

    def test_delete_teaching_record_rejects_non_htmx_request(self):
        response = DeleteTeachingRecordView.as_view()(self.request(), pk=1)
        self.assertEqual(response.status_code, 400)


class ClientViewTests(AuthenticatedViewTestCase):
    def setUp(self):
        super().setUp()
        self.client_obj = make_client()

    def test_list_uses_full_template_and_injects_form(self):
        response = ListClientView.as_view()(self.request(path="/client/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "client/list.html")
        self.assertIsInstance(response.context_data["form"], ClientForm)
        self.assertIn("custom_page_range", response.context_data)
        self.assertIn(self.client_obj, response.context_data["clients"])

    def test_list_uses_partial_template_for_htmx(self):
        with patch("todo_app.views.render", return_value=HttpResponse("partial")) as mock_render:
            response = ListClientView.as_view()(
                self.request(path="/client/", htmx=True)
            )

        self.assertEqual(response.content, b"partial")
        self.assertEqual(mock_render.call_args.args[1], "client/table-container.html")
        self.assertIn("clients", mock_render.call_args.args[2])

    def test_create_get_returns_modal_for_htmx(self):
        response = CreateClientView.as_view()(
            self.request(path="/create-client/", htmx=True)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "client/add-modal.html")
        self.assertIsInstance(response.context_data["form"], ClientForm)

    def test_create_valid_data_saves_client_and_returns_success_events(self):
        data = {
            "nama": "Client Baru",
            "kontak": "081200000099",
            "kota": "Bogor",
            "alamat": "Jalan Anggrek",
        }
        with patch("todo_app.views.render", return_value=HttpResponse("form")) as mock_render:
            response = CreateClientView.as_view()(
                self.request("post", "/create-client/", data=data, htmx=True)
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Client.objects.filter(nama="Client Baru").exists())
        payload = self.assert_hx_event(response, "clientListChanged")
        self.assertEqual(payload["showToast"]["type"], "alert-success")
        self.assertIsInstance(mock_render.call_args.args[2]["form"], ClientForm)

    def test_create_invalid_data_returns_form_errors_and_retarget_headers(self):
        initial_count = Client.objects.count()
        with patch("todo_app.views.render", return_value=HttpResponse("errors")):
            response = CreateClientView.as_view()(
                self.request(
                    "post",
                    "/create-client/",
                    data={"nama": "", "kontak": ""},
                    htmx=True,
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Client.objects.count(), initial_count)
        self.assertEqual(response["HX-Retarget"], "#add-client-form")
        self.assertEqual(response["HX-Reswap"], "outerHTML")
        self.assertEqual(
            json.loads(response["HX-Trigger"])["showToast"]["type"],
            "alert-error",
        )

    def test_edit_valid_data_updates_client_and_returns_success_event(self):
        data = {
            "nama": "Nama Diperbarui",
            "kontak": self.client_obj.kontak,
            "kota": "Bandung",
            "alamat": "Alamat baru",
        }
        response = EditClientView.as_view()(
            self.request("post", "/edit-client/1/", data=data, htmx=True),
            pk=self.client_obj.pk,
        )

        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.nama, "Nama Diperbarui")
        self.assertEqual(self.client_obj.kota, "Bandung")
        self.assert_hx_event(response, "clientListChanged")

    def test_edit_invalid_data_returns_edit_form_and_retarget_headers(self):
        data = {
            "nama": "",
            "kontak": self.client_obj.kontak,
            "kota": "Bandung",
            "alamat": "Alamat baru",
        }
        with patch("todo_app.views.render", return_value=HttpResponse("errors")) as mock_render:
            response = EditClientView.as_view()(
                self.request("post", "/edit-client/1/", data=data, htmx=True),
                pk=self.client_obj.pk,
            )

        self.assertEqual(
            response["HX-Retarget"],
            f"#edit-client-form-{self.client_obj.pk}",
        )
        self.assertEqual(mock_render.call_args.args[1], "client/edit-form-fields.html")
        self.assertFalse(mock_render.call_args.args[2]["form"].is_valid())

    def test_delete_htmx_deletes_client_and_related_user(self):
        user_id = self.client_obj.account_client_id
        response = DeleteClientView.as_view()(
            self.request("delete", "/delete-client/1/", htmx=True),
            pk=self.client_obj.pk,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Client.objects.filter(pk=self.client_obj.pk).exists())
        self.assertFalse(User.objects.filter(pk=user_id).exists())
        self.assert_hx_event(response, "clientListChanged")

    def test_search_filters_by_name_address_and_exact_contact(self):
        other = make_client(nama="Siti", kontak="082222222222", alamat="Surabaya")
        cases = [
            (self.client_obj.nama, self.client_obj),
            ("Surabaya", other),
            (other.kontak, other),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                response = SearchClientView.as_view()(
                    self.request(path="/search-client/", data={"search": query}, htmx=True)
                )
                self.assertEqual(list(response.context_data["clients"]), [expected])


class ContractViewTests(AuthenticatedViewTestCase):
    def setUp(self):
        super().setUp()
        self.client_obj = make_client()
        self.contract = make_contract(client=self.client_obj)

    def test_list_filters_payment_and_contract_status(self):
        matching = self.contract
        make_contract(client=self.client_obj, pembayaran="Lunas")
        make_contract(client=self.client_obj, contract_status="Habis")
        response = ListContractView.as_view()(
            self.request(
                path="/contract/",
                data={"pembayaran": "Kredit", "contract_status": "Berjalan"},
            )
        )

        self.assertEqual(list(response.context_data["contracts"]), [matching])
        self.assertEqual(response.context_data["current_pembayaran"], "Kredit")
        self.assertEqual(response.context_data["current_contract_status"], "Berjalan")
        self.assertIsInstance(response.context_data["form"], ContractForm)

    def test_list_uses_partial_template_for_htmx(self):
        with patch("todo_app.views.render", return_value=HttpResponse("partial")) as mock_render:
            response = ListContractView.as_view()(
                self.request(path="/contract/", htmx=True)
            )
        self.assertEqual(response.content, b"partial")
        self.assertEqual(mock_render.call_args.args[1], "contract/table-container.html")

    def test_create_valid_data_saves_contract(self):
        response = CreateContractView.as_view()(
            self.request(
                "post",
                "/create-contract/",
                data=contract_form_data(self.client_obj),
                htmx=True,
            )
        )

        self.assertEqual(Contract.objects.count(), 2)
        self.assert_hx_event(response, "contractListChanged")

    def test_create_invalid_data_returns_retarget_headers(self):
        with patch("todo_app.views.render", return_value=HttpResponse("errors")):
            response = CreateContractView.as_view()(
                self.request(
                    "post",
                    "/create-contract/",
                    data=contract_form_data(self.client_obj, total_biaya=-1),
                    htmx=True,
                )
            )
        self.assertEqual(response["HX-Retarget"], "#add-contract-form")
        self.assertEqual(Contract.objects.count(), 1)

    def test_edit_valid_data_updates_payment_and_contract_status(self):
        data = contract_form_data(
            self.client_obj,
            pembayaran="Lunas",
            contract_status="Habis",
        )
        response = EditContractView.as_view()(
            self.request("post", "/edit-contract/1/", data=data, htmx=True),
            pk=self.contract.pk,
        )

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.pembayaran, "Lunas")
        self.assertEqual(self.contract.contract_status, "Habis")
        self.assert_hx_event(response, "contractListChanged")

    def test_edit_invalid_data_returns_edit_partial(self):
        data = contract_form_data(
            self.client_obj,
            total_biaya=-100,
            pembayaran="Kredit",
            contract_status="Berjalan",
        )
        with patch("todo_app.views.render", return_value=HttpResponse("errors")) as mock_render:
            response = EditContractView.as_view()(
                self.request("post", "/edit-contract/1/", data=data, htmx=True),
                pk=self.contract.pk,
            )
        self.assertEqual(
            response["HX-Retarget"],
            f"#edit-contract-form-{self.contract.pk}",
        )
        self.assertEqual(mock_render.call_args.args[1], "contract/edit-form-fields.html")

    def test_delete_htmx_deletes_contract(self):
        response = DeleteContractView.as_view()(
            self.request("delete", "/delete-contract/1/", htmx=True),
            pk=self.contract.pk,
        )
        self.assertFalse(Contract.objects.filter(pk=self.contract.pk).exists())
        self.assert_hx_event(response, "contractListChanged")

    def test_search_filters_by_client_name(self):
        other = make_contract(
            client=make_client(nama="Siti", kontak="082222222222")
        )
        response = SearchContractView.as_view()(
            self.request(path="/search-contract/", data={"search": "Siti"}, htmx=True)
        )
        self.assertEqual(list(response.context_data["contracts"]), [other])


class PaymentViewTests(AuthenticatedViewTestCase):
    def setUp(self):
        super().setUp()
        self.contract = make_contract()
        self.payment = make_payment(contract=self.contract)

    def test_list_injects_payment_form(self):
        response = ListPaymentView.as_view()(self.request(path="/payment/"))
        self.assertEqual(response.template_name[0], "payment/list.html")
        self.assertIsInstance(response.context_data["form"], PaymentForm)
        self.assertIn(self.payment, response.context_data["payments"])

    def test_create_valid_data_saves_payment(self):
        response = CreatePaymentView.as_view()(
            self.request(
                "post",
                "/create-payment/",
                data=payment_form_data(self.contract),
                htmx=True,
            )
        )
        self.assertEqual(Payment.objects.count(), 2)
        self.assert_hx_event(response, "paymentListChanged")

    def test_create_invalid_date_returns_errors_without_saving(self):
        with patch("todo_app.views.render", return_value=HttpResponse("errors")):
            response = CreatePaymentView.as_view()(
                self.request(
                    "post",
                    "/create-payment/",
                    data=payment_form_data(self.contract, tanggal_0="invalid"),
                    htmx=True,
                )
            )
        self.assertEqual(response["HX-Retarget"], "#add-payment-form")
        self.assertEqual(Payment.objects.count(), 1)

    def test_edit_valid_data_updates_payment(self):
        data = payment_form_data(self.contract, total=750_000)
        response = EditPaymentView.as_view()(
            self.request("post", "/edit-payment/1/", data=data, htmx=True),
            pk=self.payment.pk,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.total, 750_000)
        self.assert_hx_event(response, "paymentListChanged")

    def test_delete_htmx_deletes_payment(self):
        response = DeletePaymentView.as_view()(
            self.request("delete", "/delete-payment/1/", htmx=True),
            pk=self.payment.pk,
        )
        self.assertFalse(Payment.objects.filter(pk=self.payment.pk).exists())
        self.assert_hx_event(response, "paymentListChanged")

    def test_search_by_client_name_and_payment_code(self):
        cases = [self.contract.client.nama, self.payment.kode_payment]
        for query in cases:
            with self.subTest(query=query):
                response = SearchPaymentView.as_view()(
                    self.request(path="/search-payment/", data={"search": query}, htmx=True)
                )
                self.assertEqual(list(response.context_data["payments"]), [self.payment])

    def test_search_by_month_and_invalid_month(self):
        response = SearchPaymentView.as_view()(
            self.request(path="/search-payment/", data={"search": "::1"}, htmx=True)
        )
        self.assertEqual(list(response.context_data["payments"]), [self.payment])

        for query in ("::0", "::13", "::abc"):
            with self.subTest(query=query):
                response = SearchPaymentView.as_view()(
                    self.request(path="/search-payment/", data={"search": query}, htmx=True)
                )
                self.assertEqual(list(response.context_data["payments"]), [])


class TeachingViewTests(AuthenticatedViewTestCase):
    def setUp(self):
        super().setUp()
        self.teaching = make_teaching()
        self.client_obj = self.teaching.client
        self.contract = self.teaching.kontrak

    def test_list_injects_form_and_pagination_context(self):
        response = ListTeachingView.as_view()(self.request(path="/"))
        self.assertEqual(response.template_name[0], "teaching/list.html")
        self.assertIsInstance(response.context_data["form"], TeachingForm)
        self.assertIn("custom_page_range", response.context_data)
        self.assertIn(self.teaching, response.context_data["teachings"])

    def test_list_paginates_twenty_items_per_page(self):
        for index in range(20):
            make_teaching(
                client=self.client_obj,
                contract=self.contract,
                day_of_week=(index % 6) + 1,
            )
        response = ListTeachingView.as_view()(
            self.request(path="/", data={"page": 2})
        )
        self.assertEqual(len(response.context_data["teachings"]), 1)
        self.assertEqual(response.context_data["page_obj"].number, 2)

    def test_create_valid_data_saves_teaching(self):
        response = CreateTeachingView.as_view()(
            self.request(
                "post",
                "/create-teaching/",
                data=teaching_form_data(
                    self.client_obj,
                    self.contract,
                    day_of_week=1,
                    start_time="10:00",
                    end_time="11:00",
                ),
                htmx=True,
            )
        )
        self.assertEqual(Teaching.objects.count(), 2)
        self.assert_hx_event(response, "teachingListChanged")

    def test_create_invalid_data_returns_form_partial(self):
        with patch("todo_app.views.render", return_value=HttpResponse("errors")):
            response = CreateTeachingView.as_view()(
                self.request(
                    "post",
                    "/create-teaching/",
                    data=teaching_form_data(
                        self.client_obj,
                        self.contract,
                        start_time="10:00",
                        end_time="09:00",
                    ),
                    htmx=True,
                )
            )
        self.assertEqual(response["HX-Retarget"], "#add-teach-form")
        self.assertEqual(Teaching.objects.count(), 1)

    def test_edit_valid_data_updates_schedule_and_status(self):
        data = teaching_form_data(
            self.client_obj,
            self.contract,
            day_of_week=2,
            start_time="12:00",
            end_time="13:00",
            materi="Kanji",
        )
        response = EditTeachingView.as_view()(
            self.request("post", "/edit-teaching/1/", data=data, htmx=True),
            pk=self.teaching.pk,
        )
        self.teaching.refresh_from_db()
        self.assertEqual(self.teaching.day_of_week, 2)
        self.assertEqual(self.teaching.materi, "Kanji")
        self.assertFalse(self.teaching.status_teaching)
        self.assert_hx_event(response, "teachingListChanged")

    def test_delete_htmx_deletes_teaching(self):
        response = DeleteTeachingView.as_view()(
            self.request("delete", "/delete-teaching/1/", htmx=True),
            pk=self.teaching.pk,
        )
        self.assertFalse(Teaching.objects.filter(pk=self.teaching.pk).exists())
        self.assert_hx_event(response, "teachingListChanged")

    def test_search_by_day_name_and_start_hour(self):
        cases = ["senin", "monday", "0", "::jam=8"]
        for query in cases:
            with self.subTest(query=query):
                response = SearchTeachingView.as_view()(
                    self.request(path="/search-teaching/", data={"search": query}, htmx=True)
                )
                self.assertEqual(list(response.context_data["teachings"]), [self.teaching])

    def test_search_invalid_hour_returns_empty_queryset(self):
        response = SearchTeachingView.as_view()(
            self.request(path="/search-teaching/", data={"search": "::jam=abc"}, htmx=True)
        )
        self.assertEqual(list(response.context_data["teachings"]), [])


class TeachingRecordViewTests(AuthenticatedViewTestCase):
    def setUp(self):
        super().setUp()
        self.teaching = make_teaching()
        self.contract = self.teaching.kontrak

    def post_record(self, data=None):
        return RecordTeachingView.as_view()(
            self.request(
                "post",
                f"/record-teaching/{self.teaching.pk}/",
                data=data or {},
            ),
            pk=self.teaching.pk,
        )

    def test_get_record_modal_builds_expected_context(self):
        with patch("todo_app.views.render", return_value=HttpResponse("modal")) as mock_render:
            response = RecordTeachingView.as_view()(
                self.request(path=f"/record-teaching/{self.teaching.pk}/"),
                pk=self.teaching.pk,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_render.call_args.args[1], "teaching/record-modal.html")
        context = mock_render.call_args.args[2]
        self.assertEqual(context["teaching"], self.teaching)
        self.assertIn("now_iso", context)
        self.assertIn("custom_page_range", context)

    def test_post_private_record_saves_data_and_finishes_contract_at_quota(self):
        self.contract.total_pertemuan = 1
        self.contract.save(update_fields=["total_pertemuan"])

        response = self.post_record(
            {
                "tanggal_pelaksanaan": "2026-01-05T08:30",
                "materi_realisasi": "Realisasi hiragana",
                "is_rescheduled": "on",
            }
        )

        record = TeachingRecord.objects.get()
        self.contract.refresh_from_db()
        self.assertEqual(record.kontrak, self.contract)
        self.assertEqual(record.teaching, self.teaching)
        self.assertEqual(record.materi_realisasi, "Realisasi hiragana")
        self.assertTrue(record.is_rescheduled)
        self.assertEqual(self.contract.contract_status, "Habis")
        self.assert_hx_event(response, "teachingListChanged")

    def test_post_private_record_rejects_invalid_execution_date(self):
        response = self.post_record({"tanggal_pelaksanaan": "not-a-date"})

        self.assertEqual(TeachingRecord.objects.count(), 0)
        payload = json.loads(response["HX-Trigger"])
        self.assertEqual(payload["showToast"]["type"], "alert-error")

    def test_post_private_record_rejects_full_quota(self):
        self.contract.total_pertemuan = 1
        self.contract.save(update_fields=["total_pertemuan"])
        make_record(contract=self.contract, teaching=self.teaching)

        response = self.post_record()

        self.assertEqual(TeachingRecord.objects.count(), 1)
        payload = json.loads(response["HX-Trigger"])
        self.assertEqual(payload["showToast"]["type"], "alert-warning")

    def test_post_rejects_record_when_contract_is_not_running(self):
        self.contract.contract_status = "Habis"
        self.contract.save(update_fields=["contract_status"])

        response = self.post_record()

        self.assertEqual(TeachingRecord.objects.count(), 0)
        payload = json.loads(response["HX-Trigger"])
        self.assertEqual(payload["showToast"]["type"], "alert-error")

    def test_post_institution_record_is_allowed(self):
        self.contract.tipe_kontrak = "Institusi"
        self.contract.save(update_fields=["tipe_kontrak"])

        response = self.post_record({"materi_realisasi": "Kelas institusi"})

        self.assertEqual(TeachingRecord.objects.count(), 1)
        self.assertEqual(
            json.loads(response["HX-Trigger"])["showToast"]["message"],
            "Sesi mengajar Institusi berhasil dicatat!",
        )

    def test_record_list_supports_full_and_htmx_templates(self):
        record = make_record(contract=self.contract, teaching=self.teaching)
        response = ListTeachingRecordView.as_view()(
            self.request(path="/record-teaching/")
        )
        self.assertEqual(response.template_name[0], "teaching/record-list.html")
        self.assertIn(record, response.context_data["teaching_records"])

        with patch("todo_app.views.render", return_value=HttpResponse("partial")) as mock_render:
            response = ListTeachingRecordView.as_view()(
                self.request(path="/record-teaching/", htmx=True)
            )
        self.assertEqual(response.content, b"partial")
        self.assertEqual(
            mock_render.call_args.args[1],
            "teaching/record-table-container.html",
        )

    def test_delete_record_htmx_reopens_private_contract(self):
        self.contract.total_pertemuan = 1
        self.contract.contract_status = "Habis"
        self.contract.save(update_fields=["total_pertemuan", "contract_status"])
        record = make_record(contract=self.contract, teaching=self.teaching)

        response = DeleteTeachingRecordView.as_view()(
            self.request("delete", "/delete-teaching-record/1/", htmx=True),
            pk=record.pk,
        )

        self.contract.refresh_from_db()
        self.assertFalse(TeachingRecord.objects.filter(pk=record.pk).exists())
        self.assertEqual(self.contract.contract_status, "Berjalan")
        self.assert_hx_event(response, "RecordTeachingListChanged")

    def test_search_record_by_schedule_day_hour_and_execution_day(self):
        record = make_record(contract=self.contract, teaching=self.teaching)
        for query in ("::jadwal=senin", "::jadwal=0", "::jam=8", "senin", "0"):
            with self.subTest(query=query):
                response = SearchTeachingRecordView.as_view()(
                    self.request(
                        path="/search-teaching-record/",
                        data={"search": query},
                        htmx=True,
                    )
                )
                self.assertEqual(
                    list(response.context_data["teaching_records"]),
                    [record],
                )

    def test_search_record_rejects_invalid_special_filters(self):
        make_record(contract=self.contract, teaching=self.teaching)
        for query in ("::jadwal=invalid", "::jam=24", "::jam=abc"):
            with self.subTest(query=query):
                response = SearchTeachingRecordView.as_view()(
                    self.request(
                        path="/search-teaching-record/",
                        data={"search": query},
                        htmx=True,
                    )
                )
                self.assertEqual(list(response.context_data["teaching_records"]), [])


class URLRoutingTests(SimpleTestCase):
    def test_named_class_based_routes_resolve_to_expected_views(self):
        cases = [
            ("login", CustomLoginView, []),
            ("autocomplete_client", ClientFormAutocomplete, []),
            ("autocomplete_contract", ContractFormAutocomplete, []),
            ("client_list", ListClientView, []),
            ("client_create", CreateClientView, []),
            ("client_edit", EditClientView, [1]),
            ("client_delete", DeleteClientView, [1]),
            ("search_client", SearchClientView, []),
            ("contract_list", ListContractView, []),
            ("contract_create", CreateContractView, []),
            ("contract_edit", EditContractView, [1]),
            ("contract_delete", DeleteContractView, [1]),
            ("search_contract", SearchContractView, []),
            ("payment_list", ListPaymentView, []),
            ("payment_create", CreatePaymentView, []),
            ("payment_edit", EditPaymentView, [1]),
            ("payment_delete", DeletePaymentView, [1]),
            ("search_payment", SearchPaymentView, []),
            ("teaching_list", ListTeachingView, []),
            ("teaching_create", CreateTeachingView, []),
            ("teaching_delete", DeleteTeachingView, [1]),
            ("teaching_edit", EditTeachingView, [1]),
            ("search_teaching", SearchTeachingView, []),
            ("teaching_record", RecordTeachingView, [1]),
            ("teaching_record_list", ListTeachingRecordView, []),
            ("teaching_record_delete", DeleteTeachingRecordView, [1]),
            ("search_teaching_record", SearchTeachingRecordView, []),
            ("about_me", AboutView, []),
        ]

        for name, view_class, args in cases:
            with self.subTest(route=name):
                match = resolve(reverse(f"todo_app:{name}", args=args))
                self.assertEqual(match.url_name, name)
                self.assertIs(match.func.view_class, view_class)

    def test_logout_route_resolves_to_function_view(self):
        match = resolve(reverse("todo_app:logout"))
        self.assertIs(match.func, logout_view)
