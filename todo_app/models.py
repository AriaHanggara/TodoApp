from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.crypto import get_random_string


class CustomUser(AbstractUser):
    pass


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


class Contract(models.Model):
    PAYMENT_STATUS = [
        ("Lunas", "Lunas"),
        ("Kredit", "Kredit"),
    ]
    STATUS_KONTRAK = [
        ("Habis", "Habis"),
        ("Berjalan", "Berjalan")
    ]

    ### apa lebih enak diganti payment status sama status kontrak ke boolean?

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="contracts_client"
    )

    total_pertemuan = models.PositiveIntegerField(default=0)
    total_biaya = models.PositiveBigIntegerField()
    kode_kontrak = models.CharField(max_length=4, blank=True, unique=True, editable=False)
    # kode_kontrak = models.CharField(max_length=4, default='Temporary Default')

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

    def total_teaching(self):
        return self.teaching_contract.all().count()

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

    tanggal = models.DateTimeField(auto_now_add=True)
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
                if not Pembayaran.objects.filter(kode_payment=kode).exists():
                    self.kode_payment = "PAY-" + kode
                    break

    def __str__(self):
        return f"{self.contract.client.nama} -- {self.kode_payment}"


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
        default=""
    )
    status_teaching = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "client",
                    "day_of_week",
                    "start_time",
                ],
                name="unique_client_teaching_slot",
            ),
        ]

        ordering = [
            "day_of_week",
            "start_time",
        ]

    def __str__(self):
        return f"{self.client} - {self.get_day_of_week_display()}: {self.start_time} to {self.end_time}"


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
