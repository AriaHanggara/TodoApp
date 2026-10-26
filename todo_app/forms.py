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
    dropdown_parent = "#add-contract-modal"

    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_client',
            attrs={'class': 'input input-bordered w-full'}
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].widget.attrs['data-dropdown-parent'] = self.dropdown_parent

    class Meta:
        model = Contract

        fields = [
            'client',
            'tipe_kontrak',
            "total_pertemuan",
            "total_biaya",
            'keterangan',
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
            "keterangan": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 3,
                    "placeholder": "Keterangan Kontrak",
                }
            ),
        }


class ContractUpdateForm(ContractForm):
    dropdown_parent = "#edit-contract-modal"

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


class PaymentForm(forms.ModelForm):
    dropdown_parent = '#add-payment-modal'

    contract = forms.ModelChoiceField(
        queryset=Contract.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_contract',
            attrs={'class': 'input input-bordered w-full'}
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contract'].widget.attrs['data-dropdown-parent'] = self.dropdown_parent

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
    dropdown_parent = '#edit-payment-modal'


class TeachingForm(forms.ModelForm):
    # Selector dialog tempat dropdown Select2 dirender. Di-override oleh form turunan.
    dropdown_parent = '#add-teach-modal'

    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_client',
            attrs={'class': 'input input-bordered w-full'},
        ),
    )

    kontrak = forms.ModelChoiceField(
        queryset=Contract.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_contract',
            forward=['client'],
            attrs={'class': 'input input-bordered w-full'},
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('client', 'kontrak'):
            self.fields[name].widget.attrs['data-dropdown-parent'] = self.dropdown_parent

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


class TeachingUpdateForm(TeachingForm):
    dropdown_parent = '#edit-teach-modal'

    class Meta(TeachingForm.Meta):
        fields = TeachingForm.Meta.fields + ["status_teaching"]
        widgets = {
            **TeachingForm.Meta.widgets,
            "status_teaching": forms.CheckboxInput(
                attrs={
                    "class": "toggle toggle-primary",
                }
            ),
        }
