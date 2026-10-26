"""
Unit tests for models.py.

Place this file next to models.py (e.g. todo_app/test_models.py) and run:
    python manage.py test todo_app.test_models
"""
from datetime import datetime, time
from unittest import mock, expectedFailure

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import (
    Client,
    Contract,
    Payment,
    Teaching,
    TeachingRecord,
    generate_unique_username,
)

User = get_user_model()

# Client.save() hashes a password for every auto-created user; use a fast hasher.
FAST_HASHER = override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)


def aware(year, month, day, hour=10, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def make_record(contract, teaching=None, when=None):
    return TeachingRecord.objects.create(
        kontrak=contract,
        teaching=teaching,
        tanggal_pelaksanaan=when or timezone.now(),
    )


# --------------------------------------------------------------------------- #
# generate_unique_username
# --------------------------------------------------------------------------- #
@FAST_HASHER
class GenerateUniqueUsernameTests(TestCase):
    def test_strips_spaces_and_appends_three_digit_suffix(self):
        username = generate_unique_username("A B  C")
        self.assertRegex(username, r"^ABC_\d{3}$")

    def test_retries_when_candidate_is_taken(self):
        User.objects.create_user(username="Foo_123", password="x")
        # First candidate collides, second one is free.
        with mock.patch("random.randint", side_effect=[123, 456]) as rand:
            self.assertEqual(generate_unique_username("Foo"), "Foo_456")
        self.assertEqual(rand.call_count, 2)


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
@FAST_HASHER
class ClientModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Client.objects.create(nama="Budi Santoso", kontak="0811")

    def test_create_auto_provisions_user_account(self):
        account = self.customer.account_client
        self.assertIsNotNone(account.pk)
        self.assertRegex(account.username, r"^BudiSantoso_\d{3}$")
        self.assertTrue(account.check_password("Alhamdulillah123"))

    def test_str(self):
        self.assertEqual(str(self.customer), "Budi Santoso-0811")

    def test_rename_regenerates_username_but_keeps_same_user(self):
        customer = Client.objects.get(pk=self.customer.pk)
        original_user_id = customer.account_client_id

        customer.nama = "Andi Wijaya"
        customer.save()

        user = User.objects.get(pk=original_user_id)
        self.assertRegex(user.username, r"^AndiWijaya_\d{3}$")

    def test_updating_other_fields_keeps_username(self):
        customer = Client.objects.get(pk=self.customer.pk)
        old_username = customer.account_client.username

        customer.kota = "Bogor"
        customer.save()

        customer.account_client.refresh_from_db()
        self.assertEqual(customer.account_client.username, old_username)

    def test_delete_removes_linked_user(self):
        customer = Client.objects.get(pk=self.customer.pk)
        user_id = customer.account_client_id

        customer.delete()

        self.assertFalse(Client.objects.filter(pk=customer.pk).exists())
        self.assertFalse(User.objects.filter(pk=user_id).exists())

    def test_deleting_user_cascades_to_client(self):
        self.customer.account_client.delete()
        self.assertFalse(Client.objects.filter(pk=self.customer.pk).exists())

    def test_kontak_must_be_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Client.objects.create(nama="Other", kontak="0811")

    def test_default_ordering_is_newest_first(self):
        newer = Client.objects.create(nama="Newer", kontak="0822")
        self.assertEqual(Client.objects.first(), newer)

    def test_deleting_client_cascades_to_contracts(self):
        contract = Contract.objects.create(client=self.customer, total_biaya=1)
        self.customer.delete()
        self.assertFalse(Contract.objects.filter(pk=contract.pk).exists())


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #
@FAST_HASHER
class ContractModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Client.objects.create(nama="Budi Santoso", kontak="0811")
        cls.privat = Contract.objects.create(
            client=cls.customer, total_biaya=1_000_000, total_pertemuan=4
        )
        cls.institusi = Contract.objects.create(
            client=cls.customer,
            total_biaya=5_000_000,
            total_pertemuan=0,
            tipe_kontrak="Institusi",
        )

    # --- kode_kontrak ---------------------------------------------------- #
    def test_kode_kontrak_is_generated_uppercase_4_chars(self):
        self.assertRegex(self.privat.kode_kontrak, r"^[A-Z0-9]{4}$")

    def test_kode_kontrak_is_stable_across_saves(self):
        contract = Contract.objects.get(pk=self.privat.pk)
        code = contract.kode_kontrak
        contract.keterangan = "changed"
        contract.save()
        self.assertEqual(Contract.objects.get(pk=contract.pk).kode_kontrak, code)

    def test_kode_kontrak_collision_is_retried(self):
        target = f"{Contract.__module__}.get_random_string"
        with mock.patch(target, side_effect=["abcd"]):
            first = Contract.objects.create(client=self.customer, total_biaya=1)
        self.assertEqual(first.kode_kontrak, "ABCD")

        with mock.patch(target, side_effect=["abcd", "wxyz"]) as gen:
            second = Contract.objects.create(client=self.customer, total_biaya=1)
        self.assertEqual(second.kode_kontrak, "WXYZ")
        self.assertEqual(gen.call_count, 2)

    def test_str(self):
        self.assertEqual(
            str(self.privat), f"Budi Santoso -- {self.privat.kode_kontrak}"
        )

    def test_defaults(self):
        self.assertEqual(self.privat.pembayaran, "Kredit")
        self.assertEqual(self.privat.contract_status, "Berjalan")
        self.assertEqual(self.privat.tipe_kontrak, "Privat")

    # --- payments -------------------------------------------------------- #
    def test_total_pembayaran_is_zero_without_payments(self):
        self.assertEqual(self.privat.total_pembayaran(), 0)

    def test_total_pembayaran_sums_all_payments(self):
        Payment.objects.create(contract=self.privat, tanggal=timezone.now(), total=300_000)
        Payment.objects.create(contract=self.privat, tanggal=timezone.now(), total=200_000)
        self.assertEqual(self.privat.total_pembayaran(), 500_000)

    def test_update_status_partial_payment_stays_kredit(self):
        Payment.objects.create(contract=self.privat, tanggal=timezone.now(), total=999_999)
        self.privat.update_status_pembayaran()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.pembayaran, "Kredit")

    def test_update_status_exact_payment_is_lunas(self):
        Payment.objects.create(contract=self.privat, tanggal=timezone.now(), total=1_000_000)
        self.privat.update_status_pembayaran()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.pembayaran, "Lunas")

    def test_update_status_overpayment_is_lunas(self):
        Payment.objects.create(contract=self.privat, tanggal=timezone.now(), total=2_000_000)
        self.privat.update_status_pembayaran()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.pembayaran, "Lunas")

    def test_update_status_reverts_to_kredit_when_payment_removed(self):
        payment = Payment.objects.create(
            contract=self.privat, tanggal=timezone.now(), total=1_000_000
        )
        self.privat.update_status_pembayaran()
        self.assertEqual(self.privat.pembayaran, "Lunas")

        payment.delete()
        self.privat.update_status_pembayaran()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.pembayaran, "Kredit")

    def test_update_status_only_writes_pembayaran_field(self):
        with mock.patch.object(Contract, "save") as save:
            self.privat.update_status_pembayaran()
        save.assert_called_once_with(update_fields=["pembayaran"])

    # --- progress / teaching counts ------------------------------------- #
    def test_total_mengajar_counts_records(self):
        self.assertEqual(self.privat.total_mengajar, 0)
        make_record(self.privat)
        make_record(self.privat)
        self.assertEqual(self.privat.total_mengajar, 2)

    def test_progress_institusi_is_always_100(self):
        self.assertEqual(self.institusi.progress_percentage, 100)

    def test_progress_is_zero_when_total_pertemuan_is_zero(self):
        contract = Contract.objects.create(
            client=self.customer, total_biaya=1, total_pertemuan=0
        )
        make_record(contract)
        self.assertEqual(contract.progress_percentage, 0)

    def test_progress_half_way(self):
        make_record(self.privat)
        make_record(self.privat)
        self.assertEqual(self.privat.progress_percentage, 50)

    def test_progress_is_rounded(self):
        contract = Contract.objects.create(
            client=self.customer, total_biaya=1, total_pertemuan=3
        )
        make_record(contract)
        self.assertEqual(contract.progress_percentage, 33)  # 33.33 -> 33

    def test_progress_is_capped_at_100(self):
        for _ in range(6):  # quota is 4
            make_record(self.privat)
        self.assertEqual(self.privat.progress_percentage, 100)

    # --- check_and_update_status ---------------------------------------- #
    def test_status_unchanged_below_quota(self):
        for _ in range(3):
            make_record(self.privat)
        self.privat.check_and_update_status()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Berjalan")

    def test_status_becomes_habis_when_quota_reached(self):
        for _ in range(4):
            make_record(self.privat)
        self.privat.check_and_update_status()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Habis")

    def test_status_becomes_habis_when_quota_exceeded(self):
        for _ in range(5):
            make_record(self.privat)
        self.privat.check_and_update_status()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Habis")

    def test_institusi_never_becomes_habis(self):
        self.institusi.total_pertemuan = 1  # even with a quota set
        self.institusi.save()
        for _ in range(3):
            make_record(self.institusi)
        self.institusi.check_and_update_status()
        self.institusi.refresh_from_db()
        self.assertEqual(self.institusi.contract_status, "Berjalan")

    def test_privat_without_quota_never_becomes_habis(self):
        contract = Contract.objects.create(
            client=self.customer, total_biaya=1, total_pertemuan=0
        )
        make_record(contract)
        contract.check_and_update_status()
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, "Berjalan")


# --------------------------------------------------------------------------- #
# Payment
# --------------------------------------------------------------------------- #
@FAST_HASHER
class PaymentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Client.objects.create(nama="Budi Santoso", kontak="0811")
        cls.contract = Contract.objects.create(client=cls.customer, total_biaya=1_000)
        cls.payment = Payment.objects.create(
            contract=cls.contract, tanggal=timezone.now(), total=500
        )

    def test_kode_payment_has_pay_prefix(self):
        self.assertRegex(self.payment.kode_payment, r"^PAY-[A-Z0-9]{4}$")

    def test_kode_payment_is_stable_across_saves(self):
        payment = Payment.objects.get(pk=self.payment.pk)
        code = payment.kode_payment
        payment.total = 600
        payment.save()
        self.assertEqual(Payment.objects.get(pk=payment.pk).kode_payment, code)

    def test_str(self):
        self.assertEqual(
            str(self.payment), f"Budi Santoso -- {self.payment.kode_payment}"
        )

    @expectedFailure
    def test_kode_payment_fits_max_length(self):
        """BUG: 'PAY-' + 4 chars = 8 chars, but max_length is 4.

        SQLite doesn't enforce varchar length so this slips through locally,
        but PostgreSQL/MySQL will raise DataError. Remove @expectedFailure
        after raising max_length (e.g. to 8) and adding a migration.
        """
        max_len = Payment._meta.get_field("kode_payment").max_length
        self.assertLessEqual(len(self.payment.kode_payment), max_len)

    @expectedFailure
    def test_kode_payment_collision_is_retried(self):
        """BUG: the uniqueness check compares the un-prefixed code, so it can
        never detect a collision with an existing 'PAY-XXXX' value."""
        target = f"{Payment.__module__}.get_random_string"
        with mock.patch(target, side_effect=["abcd"]):
            Payment.objects.create(contract=self.contract, tanggal=timezone.now(), total=1)
        with mock.patch(target, side_effect=["abcd", "wxyz"]):
            second = Payment.objects.create(
                contract=self.contract, tanggal=timezone.now(), total=1
            )
        self.assertEqual(second.kode_payment, "PAY-WXYZ")


# --------------------------------------------------------------------------- #
# Teaching.clean()
# --------------------------------------------------------------------------- #
@FAST_HASHER
class TeachingCleanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_a = Client.objects.create(nama="Budi Santoso", kontak="0811")
        cls.client_b = Client.objects.create(nama="Siti Aminah", kontak="0899")
        cls.contract_a = Contract.objects.create(client=cls.client_a, total_biaya=1)
        cls.contract_b = Contract.objects.create(client=cls.client_b, total_biaya=1)
        # Existing slot: Monday 10:00 - 11:00 (client A)
        cls.existing = Teaching.objects.create(
            client=cls.client_a,
            kontrak=cls.contract_a,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

    def build(self, **overrides):
        data = dict(
            client=self.client_b,
            kontrak=self.contract_b,
            day_of_week=0,
            start_time=time(12, 0),
            end_time=time(13, 0),
        )
        data.update(overrides)
        return Teaching(**data)

    # --- happy paths ----------------------------------------------------- #
    def test_valid_slot_passes(self):
        self.build().clean()  # no exception

    def test_adjacent_slot_after_is_not_an_overlap(self):
        self.build(start_time=time(11, 0), end_time=time(12, 0)).clean()

    def test_adjacent_slot_before_is_not_an_overlap(self):
        self.build(start_time=time(9, 0), end_time=time(10, 0)).clean()

    def test_same_time_on_different_day_is_allowed(self):
        self.build(
            day_of_week=1, start_time=time(10, 0), end_time=time(11, 0)
        ).clean()

    def test_existing_record_can_be_cleaned_without_self_conflict(self):
        self.existing.clean()

    def test_editing_own_slot_to_overlap_itself_is_allowed(self):
        slot = Teaching.objects.get(pk=self.existing.pk)
        slot.start_time = time(10, 30)
        slot.end_time = time(11, 30)
        slot.clean()

    # --- contract / client ownership ------------------------------------ #
    def test_contract_must_belong_to_selected_client(self):
        teaching = self.build(client=self.client_b, kontrak=self.contract_a)
        with self.assertRaises(ValidationError) as ctx:
            teaching.clean()
        self.assertIn("kontrak", ctx.exception.message_dict)

    # --- time ordering --------------------------------------------------- #
    def test_end_before_start_is_rejected(self):
        teaching = self.build(start_time=time(15, 0), end_time=time(14, 0))
        with self.assertRaises(ValidationError) as ctx:
            teaching.clean()
        self.assertIn("end_time", ctx.exception.message_dict)

    def test_end_equal_to_start_is_rejected(self):
        teaching = self.build(start_time=time(15, 0), end_time=time(15, 0))
        with self.assertRaises(ValidationError) as ctx:
            teaching.clean()
        self.assertIn("end_time", ctx.exception.message_dict)

    # --- overlap detection ---------------------------------------------- #
    def assertOverlaps(self, start, end, **overrides):
        teaching = self.build(start_time=start, end_time=end, **overrides)
        with self.assertRaises(ValidationError) as ctx:
            teaching.clean()
        errors = ctx.exception.message_dict
        self.assertIn("start_time", errors)
        self.assertIn("end_time", errors)
        return errors

    def test_overlap_at_start_of_existing(self):
        self.assertOverlaps(time(9, 30), time(10, 30))

    def test_overlap_at_end_of_existing(self):
        self.assertOverlaps(time(10, 30), time(11, 30))

    def test_new_slot_inside_existing(self):
        self.assertOverlaps(time(10, 15), time(10, 45))

    def test_new_slot_engulfs_existing(self):
        self.assertOverlaps(time(9, 0), time(12, 0))

    def test_identical_slot(self):
        self.assertOverlaps(time(10, 0), time(11, 0))

    def test_overlap_applies_across_clients(self):
        # client_b clashing with client_a's slot -> still a conflict
        self.assertOverlaps(time(10, 30), time(11, 30), client=self.client_b,
                            kontrak=self.contract_b)

    def test_overlap_error_message_names_conflicting_client_and_times(self):
        errors = self.assertOverlaps(time(10, 30), time(11, 30))
        message = errors["start_time"][0]
        self.assertIn("Budi Santoso", message)
        self.assertIn("10:00 - 11:00", message)

    # --- properties ------------------------------------------------------ #
    def test_total_mengajar_and_progress_delegate_to_contract(self):
        self.contract_a.total_pertemuan = 4
        self.contract_a.save()
        make_record(self.contract_a, self.existing)
        teaching = Teaching.objects.get(pk=self.existing.pk)
        self.assertEqual(teaching.total_mengajar, 1)
        self.assertEqual(teaching.progress_percentage, 25)

    def test_str(self):
        self.assertIn("Monday", str(self.existing))


# --------------------------------------------------------------------------- #
# TeachingRecord
# --------------------------------------------------------------------------- #
@FAST_HASHER
class TeachingRecordModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Client.objects.create(nama="Budi Santoso", kontak="0811")
        cls.privat = Contract.objects.create(
            client=cls.customer, total_biaya=1, total_pertemuan=2
        )
        cls.institusi = Contract.objects.create(
            client=cls.customer, total_biaya=1, tipe_kontrak="Institusi"
        )
        cls.slot = Teaching.objects.create(
            client=cls.customer,
            kontrak=cls.privat,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

    def test_str_format(self):
        record = make_record(self.privat, when=aware(2025, 1, 6, 10, 30))
        self.assertEqual(str(record), "Budi Santoso - 06/01/2025 10:30")

    def test_ordering_is_latest_first(self):
        old = make_record(self.privat, when=aware(2025, 1, 6))
        new = make_record(self.privat, when=aware(2025, 1, 13))
        self.assertEqual(list(TeachingRecord.objects.all()), [new, old])

    def test_deleting_teaching_keeps_record_with_null_teaching(self):
        record = make_record(self.privat, self.slot)
        self.slot.delete()
        record.refresh_from_db()
        self.assertIsNone(record.teaching)

    def test_delete_reopens_habis_privat_contract_below_quota(self):
        first = make_record(self.privat)
        make_record(self.privat)
        self.privat.check_and_update_status()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Habis")

        first.delete()

        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Berjalan")

    def test_delete_keeps_habis_when_quota_still_met(self):
        records = [make_record(self.privat) for _ in range(3)]  # quota is 2
        Contract.objects.filter(pk=self.privat.pk).update(contract_status="Habis")

        records[0].delete()  # 2 left == quota

        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Habis")

    def test_delete_does_not_touch_status_of_running_contract(self):
        record = make_record(self.privat)
        record.delete()
        self.privat.refresh_from_db()
        self.assertEqual(self.privat.contract_status, "Berjalan")

    def test_delete_does_not_reopen_institusi_contract(self):
        record = make_record(self.institusi)
        Contract.objects.filter(pk=self.institusi.pk).update(contract_status="Habis")
        record.delete()
        self.institusi.refresh_from_db()
        self.assertEqual(self.institusi.contract_status, "Habis")

    def test_delete_does_not_reopen_privat_contract_without_quota(self):
        contract = Contract.objects.create(
            client=self.customer, total_biaya=1, total_pertemuan=0
        )
        record = make_record(contract)
        Contract.objects.filter(pk=contract.pk).update(contract_status="Habis")
        record.delete()
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, "Habis")
