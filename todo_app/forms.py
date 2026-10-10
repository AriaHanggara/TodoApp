from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from .models import (Client, Contract, Payment, Teaching, MaterialFile)


class ClientForm(forms.ModelForm):
	class Meta:
		model = Client

		fields = [
			"nama",
			"kontak",
            "kota",
			"alamat",
		]

		widgets = {
            "nama": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Nama client",
                }
            ),
            "kontak": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Nomor telepon / WhatsApp",
                }
            ),
            "kota": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Kota",
                }
            ),
            "alamat": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 3,
                    "placeholder": "Alamat client",
                }
            ),
		}
	# def clean_nama(self):
	# 	pass 
	# def clean_kontak(self):
	# 	pass


class ContractForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_client',
            attrs={
                'data-dropdown-parent': '#add-contract-modal',
                'class': 'input input-bordered w-full'
            }
        )
    )

    class Meta:
        model = Contract

        fields = [
            'client',
            'tipe_kontrak',
            "total_pertemuan",
            "total_biaya",
        ]

        widgets = {
            "tipe_kontrak": forms.Select(
                attrs={
                    "class": "select select-bordered w-full",
                }
            ),
            "total_pertemuan": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": 0,
                    # "required": 'true',
                }
            ),
            "total_biaya": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": 0,
                }
            ),
            "pembayaran": forms.Select(
                attrs={
                    "class": "select select-primary",
                    "min": 0,
                }
            ),
            "contract_status": forms.Select(
                attrs={
                    "class": "select select-primary",
                    "min": 0,
                }
            ),
        }


class ContractUpdateForm(ContractForm):
    class Meta(ContractForm.Meta):
        fields = ContractForm.Meta.fields + ["pembayaran", "contract_status"]
        widgets = {
            **ContractForm.Meta.widgets,
            "pembayaran": forms.Select(
                attrs={
                    "class": "select select-primary",
                    "min": 0,
                }
            ),
            "contract_status": forms.Select(
                attrs={
                    "class": "select select-primary",
                    "min": 0,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'client' in self.fields:
            self.fields['client'].widget.attrs['data-dropdown-parent'] = '#edit-contract-modal'


class PaymentForm(forms.ModelForm):
    contract = forms.ModelChoiceField(
        queryset=Contract.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_contract',
            attrs={
                'data-dropdown-parent': '#add-payment-modal',
                'class': 'input input-bordered w-full'
            }
        )
    )

    # tanggal = forms.DateTimeField(widget=forms.SplitDateTimeWidget(attrs={'attrs': 'attrs'}))
    # Definisikan field tanggal secara eksplisit dengan SplitDateTimeField dan SplitDateTimeWidget
    tanggal = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_format='%Y-%m-%d',
            time_format='%H:%M',
            date_attrs={
                'type': 'date',
                'class': 'input input-bordered w-full datepicker',
            },
            time_attrs={
                'type': 'time',
                'class': 'input input-bordered w-full timepicker',
            },
        )
    )

    class Meta:
        model = Payment

        fields = [
            "contract",
            "tanggal",
            "total",
        ]

        widgets = {
            "total": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": 1,
                    "placeholder": "Jumlah pembayaran",
                }
            ),
        }


class PaymentUpdateForm(PaymentForm):
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if 'contract' in self.fields:
                self.fields['contract'].widget.attrs['data-dropdown-parent'] = '#edit-payment-modal'


class TeachingForm(forms.ModelForm):
    client = forms.ModelChoiceField(
            queryset=Client.objects.all(),
            widget=autocomplete.ModelSelect2(
                url='todo_app:autocomplete_client',
                attrs={
                    'data-dropdown-parent': '#add-teach-modal',
                    'class': 'input input-bordered w-full'
                }
            )
        )

    kontrak = forms.ModelChoiceField(
            queryset=Contract.objects.all(),
            widget=autocomplete.ModelSelect2(
                url='todo_app:autocomplete_contract',
                attrs={
                    'data-dropdown-parent': '#add-teach-modal',
                    'class': 'input input-bordered w-full'
                }
            )
        )
    
    class Meta:
        model = Teaching

        fields = [
            "client",
            "kontrak",
            "day_of_week",
            "start_time",
            "end_time",
            "materi",
        ]

        widgets = {
            "day_of_week": forms.Select(
                attrs={
                    "class": "input input-bordered w-full"
                }
            ),
            "start_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time",
                    "placeholder": "Waktu mulai",
                    "class": "input input-bordered w-full",
                },
            ),

            "end_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time",
                    "class": "input input-bordered w-full",
                },
            ),

            "materi": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 3,
                    "placeholder": "Materi teaching...",
                },
            ),
        }

    # def clean(self):
    #     cleaned_data = super().clean()

    #     start_time = cleaned_data.get("start_time")
    #     end_time = cleaned_data.get("end_time")

    #     if start_time and end_time:
    #         if start_time >= end_time:
    #             self.add_error(
    #                 "end_time",
    #                 "Jam selesai harus lebih besar dari jam mulai.",
    #             )

    #     return cleaned_data


class TeachingUpdateForm(TeachingForm):
    class Meta(TeachingForm.Meta):  # 1. Warisi Meta milik TeachingForm
        # 2. Tambahkan 'status_teaching' ke daftar fields milik parent
        fields = TeachingForm.Meta.fields + ["status_teaching"]

        # 3. Gabungkan widget dari parent dengan widget baru untuk status_teaching
        widgets = {
            **TeachingForm.Meta.widgets,
            "status_teaching": forms.CheckboxInput(
                attrs={
                    "class": "toggle toggle-primary",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 4. (Opsional) Jika ID modal edit berbeda dari modal add (#edit-teach-modal)
        if 'client' in self.fields:
            self.fields['client'].widget.attrs['data-dropdown-parent'] = '#edit-teach-modal'
        if 'kontrak' in self.fields:
            self.fields['kontrak'].widget.attrs['data-dropdown-parent'] = '#edit-teach-modal'