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
            "total_pertemuan",
            "total_biaya",
        ]

        widgets = {
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


class ContractUpdateForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='todo_app:autocomplete_client',
            attrs={
                'data-dropdown-parent': '#edit-contract-modal',
                'class': 'input input-bordered w-full'
            }
        )
    )

    class Meta:
        model = Contract

        fields = [
            'client',
            "total_pertemuan",
            "total_biaya",
            "pembayaran",
            "contract_status",
        ]

        widgets = {
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

    class Meta:
        model = Payment

        fields = [
            "contract"
            "tanggal",
            "total",
        ]

        widgets = {
            "tanggal": forms.SplitDateTimeField(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            )
            "total": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": 1,
                    "placeholder": "Jumlah pembayaran",
                }
            ),
        }


class TeachingForm(forms.ModelForm):

    class Meta:
        model = Teaching

        fields = [
            "day_of_week",
            "start_time",
            "end_time",
            "materi",
            "status_teaching",
        ]

        widgets = {
            "day_of_week": forms.HiddenInput(),

            "start_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time",
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

            "status_teaching": forms.CheckboxInput(
                attrs={
                    "class": "toggle toggle-primary",
                },
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            if start_time >= end_time:
                self.add_error(
                    "end_time",
                    "Jam selesai harus lebih besar dari jam mulai.",
                )

        return cleaned_data