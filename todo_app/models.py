from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
import random
from django.contrib.auth import get_user_model
from django.utils import timezone


def generate_unique_username(data):
    while True:
        rand_num = random.randint(100, 999)
        data = data.replace(' ', '')
        new_username = f"{data}_{rand_num}"

        if not User.objects.filter(username=new_username).exists():
            return new_username

            
class CustomUser(AbstractUser):
    pass

User = get_user_model()
class Client(models.Model):
    account_client = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_account')
    nama = models.CharField(max_length=255)
    kontak = models.CharField(max_length=25, unique=True)
    kota = models.CharField(max_length=100, default="", blank=True)
    alamat = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nama}-{self.kontak}"

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        User = get_user_model()

        if not self.pk:
            # 1. Jika data baru (Create Client), otomatis buatkan akun User baru
            new_user = User.objects.create_user(
                username=generate_unique_username(self.nama),
                password='Alhamdulillah123',
            )
            self.account_client = new_user
        else:
            # 2. Jika data lama (Update Client), cek apakah nama berubah
            old_client = Client.objects.get(pk=self.pk)
            if old_client.nama != self.nama and self.account_client:
                self.account_client.username = generate_unique_username(self.nama)
                self.account_client.save()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # 1. Simpan referensi ke akun User terkait sebelum Client dihapus
        user = self.account_client
        
        # 2. Hapus objek Client dari database
        super().delete(*args, **kwargs)
        
        # 3. Hapus akun User terkait (jika ada)
        if user:
            user.delete()


class Contract(models.Model):
    PAYMENT_STATUS = [
        ("Lunas", "Lunas"),
        ("Kredit", "Kredit"),
    ]
    STATUS_KONTRAK = [
        ("Habis", "Habis"),
        ("Berjalan", "Berjalan")
    ]
    TIPE_KONTRAK = [
        ("Privat", "Privat"),
        ("Institusi", "Institusi"),
    ]
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="contracts_client"
    )

    total_pertemuan = models.PositiveIntegerField(default=0)
    total_biaya = models.PositiveBigIntegerField()
    kode_kontrak = models.CharField(max_length=4, blank=True, unique=True, editable=False)
    tipe_kontrak = models.CharField(
            max_length=10,
            choices=TIPE_KONTRAK,
            default="Privat"
        )

    pembayaran = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS,
        default="Kredit"
    )

    contract_status = models.CharField(
        max_length=10,
        choices=STATUS_KONTRAK,
        default="Berjalan"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # return f"{self.client.nama}:{self.get_pembayaran_display()} - {self.get_contract_status_display()}/{self.total_teaching()} pertemuan."
        return f"{self.client.nama} -- {self.kode_kontrak}"

    def total_pembayaran(self):
        return sum(
            payment.total
            for payment in self.payments.all()
        )

    def update_status_pembayaran(self):
        if self.total_pembayaran() >= self.total_biaya:
            self.pembayaran = "Lunas"
        else:
            self.pembayaran = "Kredit"

        self.save(update_fields=["pembayaran"])

    @property
    def total_mengajar(self):
        """Menghitung total sesi mengajar yang sudah dilakukan pada kontrak ini."""
        return self.records.count()

    @property
    def progress_percentage(self):
        """Menghitung persentase progres (hanya berlaku untuk Privat)."""
        if self.tipe_kontrak == "Institusi":
            return 100  # Institusi berjalan dinamis tanpa batas persentase baku
        
        if not self.total_pertemuan or self.total_pertemuan == 0:
            return 0
        persen = (self.total_mengajar / self.total_pertemuan) * 100
        return min(100, round(persen))

    def check_and_update_status(self):
        """Otomatis ubah status kontrak menjadi 'Habis' hanya jika Privat dan kuota terpenuhi."""
        if self.tipe_kontrak == "Privat" and self.total_pertemuan:
            if self.total_mengajar >= self.total_pertemuan:
                self.contract_status = "Habis"
                self.save(update_fields=["contract_status"])

    def save(self, *args, **kwargs):
        # Only generate a code if it hasn't been set yet (on creation)
        if not self.kode_kontrak:
            while True:
                kode = get_random_string(length=4).upper()
                if not Contract.objects.filter(kode_kontrak=kode).exists():
                    self.kode_kontrak = kode
                    break
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']


class Payment(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    tanggal = models.DateTimeField()
    total = models.PositiveBigIntegerField()
    kode_payment = models.CharField(max_length=4, blank=True, unique=True, editable=False)
    # kode_payment = models.CharField(max_length=4, default='Temporary Default')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Only generate a code if it hasn't been set yet (on creation)
        if not self.kode_payment:
            while True:
                kode = get_random_string(length=4).upper()
                if not Payment.objects.filter(kode_payment=kode).exists():
                    self.kode_payment = "PAY-" + kode
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract.client.nama} -- {self.kode_payment}"

    class Meta:
            ordering = ['-created_at']


class Teaching(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="teachings"
    )

    kontrak = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="teaching_contract",
        default="",
    )

    DAY_OF_WEEK_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    # Stores the day of the week as an integer (0-6)
    day_of_week = models.PositiveSmallIntegerField(
        choices=DAY_OF_WEEK_CHOICES,
        validators=[MinValueValidator(0), MaxValueValidator(6)]
    )
    # Start and end times for the recurring weekly slot
    start_time = models.TimeField()
    end_time = models.TimeField()

    materi = models.TextField(
        default="", blank=True
    )
    status_teaching = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=[
        #             "client",
        #             "day_of_week",
        #             "start_time",
        #         ],
        #         name="unique_client_teaching_slot",
        #     ),
        # ]

        ordering = [
            "day_of_week",
            "start_time",
        ]

    def __str__(self):
        return f"{self.client} - {self.get_day_of_week_display()}: {self.start_time} to {self.end_time}"

    def clean(self):
        super().clean()
        
        # 1. Validasi: Kontrak harus milik Client yang dipilih
        if self.client and self.kontrak:
            if self.kontrak.client != self.client:
                raise ValidationError({
                    "kontrak": "Kontrak yang dipilih tidak sesuai dengan Client yang dipilih."
                })

        # 2. Validasi: Jam Selesai harus lebih besar dari Jam Mulai
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({
                    "end_time": "Waktu selesai harus lebih besar dari waktu mulai."
                })
            
            # 3. Validasi: Pengecekan Bentrok Waktu (Overlapping) pada Hari yang Sama
            overlapping_teachings = Teaching.objects.filter(
                day_of_week=self.day_of_week,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )

            # Jika sedang update data (instance sudah ada di database), kecualikan dirinya sendiri
            if self.pk:
                overlapping_teachings = overlapping_teachings.exclude(pk=self.pk)

            if overlapping_teachings.exists():
                konflik = overlapping_teachings.first()
                pesan_error = f"Jadwal bentrok dengan {konflik.client.nama} pada jam {konflik.start_time.strftime('%H:%M')} - {konflik.end_time.strftime('%H:%M')}."
                
                raise ValidationError({
                    "start_time": pesan_error,
                    "end_time": pesan_error
                })

    @property
    def total_mengajar(self):
        return self.kontrak.total_mengajar if self.kontrak else 0

    @property
    def progress_percentage(self):
        return self.kontrak.progress_percentage if self.kontrak else 0


class MaterialFile(models.Model):
    file = models.FileField(
        upload_to="materials/"
    )

    tanggal = models.DateTimeField(
        auto_now_add=True
    )

    materi = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


class TeachingRecord(models.Model):
    """Model rekam jejak / jurnal sesi mengajar yang telah dilaksanakan."""
    kontrak = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="records"
    )
    teaching = models.ForeignKey(
        Teaching,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records"
    )
    tanggal_pelaksanaan = models.DateTimeField(default=timezone.now)
    materi_realisasi = models.TextField(blank=True, default="")
    is_rescheduled = models.BooleanField(
        default=False,
        verbose_name="Jadwal Pengganti / Berubah"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tanggal_pelaksanaan']

    def __str__(self):
        return f"{self.kontrak.client.nama} - {self.tanggal_pelaksanaan.strftime('%d/%m/%Y %H:%M')}"