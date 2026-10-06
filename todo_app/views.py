from django.shortcuts import render, redirect, HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseNotAllowed, Http404
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.views.generic.base import TemplateView
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
import random
from .models import (
        Client, Contract, Payment, Teaching, MaterialFile 
    )
from .forms import (
        ClientForm, TeachingForm, ContractForm, ContractUpdateForm, PaymentForm
    )
import json
from dal import autocomplete



######## Url for autocomplete ########
class ClientFormAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Ensure user is authenticated if necessary
        if not self.request.user.is_authenticated:
            return Client.objects.none()

        qs = Client.objects.all()

        if self.q:
            qs = qs.filter(Q(nama__icontains=self.q) | Q(alamat__icontains=self.q) | Q(kontak=self.q))

        return qs


class ContractFormAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Ensure user is authenticated if necessary
        if not self.request.user.is_authenticated:
            return Contract.objects.none()

        qs = Contract.objects.all()

        if self.q:
            qs = qs.filter(Q(contract__client__nama__icontains=self.q) | Q(contract__client__alamat__icontains=self.q) | Q(contract__client__kontak=self.q))

        return qs
######## End Url ########


######## Authentication ########
# LOGIN VIEW
class CustomLoginView(LoginView):
    template_name = "authentication/login.html"
    redirect_authenticated_user = True # Redirect authenticated users to the home page
    
    # This method is called to get the success URL after login
    def get_success_url(self):
        return reverse_lazy("todo_app:teaching_list")


# LOGOUT VIEW USING FUNCTION BASED VIEW
@login_required(login_url="todo_app:login")
def logout_view(request):
    auth_logout(request)  # Remove the user from the session
    return redirect("todo_app:login")
######## End Authentication ########


######## Client ########
class ListClientView(LoginRequiredMixin, ListView):
    model = Client
    context_object_name = "clients"
    template_name = "client/list.html"
    paginate_by = 20 # Data per page

    def render_to_response(self, context, **response_kwargs):
        """Kembalikan partial container tabel (termasuk pagination) jika request HTMX"""
        if self.request.headers.get("HX-Request") == "true":
            # Kita arahkan ke berkas baru yang membungkus tabel DAN komponen pagination
            return render(self.request, "client/table-container.html", context)
        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        return Client.objects.all()

    def get_context_data(self, **kwargs):
        """Inject client creation form into the context."""
        context = super().get_context_data(**kwargs)
        context["form"] = ClientForm

        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context

#@login_required(login_url="todo_app:login") ## Error if use this
def generate_unique_username(data):
    while True:
        rand_num = random.randint(100, 999)
        data = data.replace(' ', '')
        new_username = f"{data}_{rand_num}"

        if not User.objects.filter(username=new_username).exists():
            return new_username

class CreateClientView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "client/add-modal.html"

    def form_valid(self, form):
        client = form.save(commit=False)
        new_user = User.objects.create_user(
            username=generate_unique_username(client.nama),
            password='Alhamdulillah123',
        )
        client.account_client = new_user
        client.save()

        # Render kembali form kosong agar siap digunakan untuk penambahan berikutnya
        fresh_form = ClientForm()
        response = render(self.request, "client/form-fields.html", {"form": fresh_form})
        
        payload = {
            "clientListChanged": {},
            "showToast": {"message": "Client berhasil ditambahkan!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang partial form-fields beserta errornya
        response = render(self.request, "client/form-fields.html", {"form": form})
        
        # Targetkan ulang langsung ke ID form-nya
        response["HX-Retarget"] = "#add-client-form"
        response["HX-Reswap"] = "outerHTML"
        
        payload = {
            "showToast": {"message": "Gagal menyimpan. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class DeleteClientView(LoginRequiredMixin, DeleteView):
    model = Client
    success_url = reverse_lazy("todo_app:client_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        self.object.account_client.delete()
        
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "clientListChanged": {},
                "showToast": {"message": "Client berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response
            
        return super().delete(request, *args, **kwargs)


class EditClientView(LoginRequiredMixin, UpdateView):
    model = Client
    context_object_name = "client"
    form_class = ClientForm
    pk_url_kwarg = "pk"
    template_name = "client/edit-modal.html"

    def get_queryset(self):
        return Client.objects.all()

    def form_valid(self, form):
        old_data = self.get_object()
        client = form.save(commit=False)
        
        # Jika nama berubah, update username pada akun terkait
        if client.nama != old_data.nama:
            user = User.objects.get(username=old_data.account_client.username)
            user.username = generate_unique_username(client.nama)
            user.save()
            
        client.save()

        # Kirim HTMX Trigger JSON untuk merefresh daftar & menampilkan toast sukses
        response = HttpResponse("")
        payload = {
            "clientListChanged": {},
            "showToast": {"message": "Client berhasil diperbarui!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang form fields dengan pesan error
        response = render(self.request, "client/edit-form-fields.html", {"form": form, "client": self.get_object()})
        
        # Retarget langsung ke ID form edit
        response["HX-Retarget"] = f"#edit-client-form-{self.get_object().id}"
        response["HX-Reswap"] = "outerHTML"
        
        # Kirim toast peringatan gagal
        payload = {
            "showToast": {"message": "Gagal memperbarui. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class SearchClientView(LoginRequiredMixin, ListView):
    """Search client by name or address with pagination support."""
    model = Client
    context_object_name = "clients"
    template_name = "client/table-container.html"
    paginate_by = 20  # Sesuaikan dengan paginate_by di ListClientView

    def dispatch(self, request, *args, **kwargs):
        # Tolak jika diakses langsung dari browser tanpa melalui HTMX
        if not request.headers.get('HX-Request'):
            raise Http404("The requested item does not exist.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.GET.get("search", "").strip()
        if query:
            return Client.objects.filter(Q(nama__icontains=query) | Q(alamat__icontains=query) | Q(kontak=query))
        return Client.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        paginator = page_obj.paginator

        context['custom_page_range'] = paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context
######## End Client ########


######## Contract ########
class ListContractView(LoginRequiredMixin, ListView):
    model = Contract
    context_object_name = "contracts"
    template_name = "contract/list.html"
    paginate_by = 20 # Data per page

    def render_to_response(self, context, **response_kwargs):
        """Kembalikan partial container tabel (termasuk pagination) jika request HTMX"""
        if self.request.headers.get("HX-Request") == "true":
            # Kita arahkan ke berkas baru yang membungkus tabel DAN komponen pagination
            return render(self.request, "contract/table-container.html", context)
        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        queryset = Contract.objects.all()
        # Tangkap kedua parameter filter
        pembayaran = self.request.GET.get("pembayaran", "").strip()
        contract_status = self.request.GET.get("contract_status", "").strip()

        # Filter berdasarkan pembayaran jika ada
        if pembayaran:
            queryset = queryset.filter(pembayaran=pembayaran)

        # Filter berdasarkan status kontrak jika ada
        if contract_status:
            queryset = queryset.filter(contract_status=contract_status)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        """Inject contract creation form into the context."""
        context = super().get_context_data(**kwargs)
        context["form"] = ContractForm
        
        # Gunakan or "" untuk mencegah nilai None masuk ke template
        context['current_pembayaran'] = self.request.GET.get("pembayaran", "").strip()
        context['current_contract_status'] = self.request.GET.get("contract_status", "").strip()

        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context


class CreateContractView(LoginRequiredMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = "client/add-modal.html"

    def form_valid(self, form):
        # contract = form.save(commit=False)
        # contract.save()
        form.save()

        # Render kembali form kosong agar siap digunakan untuk penambahan berikutnya
        fresh_form = ContractForm()
        response = render(self.request, "contract/form-fields.html", {"form": fresh_form})
        
        payload = {
            "contractListChanged": {},
            "showToast": {"message": "Kontak berhasil ditambahkan!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang partial form-fields beserta errornya
        response = render(self.request, "contract/form-fields.html", {"form": form})
        
        # Targetkan ulang langsung ke ID form-nya
        response["HX-Retarget"] = "#add-contract-form"
        response["HX-Reswap"] = "outerHTML"
        
        payload = {
            "showToast": {"message": "Gagal menyimpan. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class DeleteContractView(LoginRequiredMixin, DeleteView):
    model = Contract
    success_url = reverse_lazy("todo_app:contract_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "contractListChanged": {},
                "showToast": {"message": "Kontrak berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response
            
        return super().delete(request, *args, **kwargs)


class EditContractView(LoginRequiredMixin, UpdateView):
    model = Contract
    context_object_name = "contract"
    form_class = ContractUpdateForm
    pk_url_kwarg = "pk"
    template_name = "contract/edit-modal.html"

    def get_queryset(self):
        return Contract.objects.all()

    def form_valid(self, form):
        contract = form.save(commit=False)
        contract.save()

        # Kirim HTMX Trigger JSON untuk merefresh daftar & menampilkan toast sukses
        response = HttpResponse("")
        payload = {
            "contractListChanged": {},
            "showToast": {"message": "Kontrak berhasil diperbarui!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang form fields dengan pesan error
        response = render(self.request, "contract/edit-form-fields.html", {"form": form, "contract": self.get_object()})
        
        # Retarget langsung ke ID form edit
        response["HX-Retarget"] = f"#edit-contract-form-{self.get_object().id}"
        response["HX-Reswap"] = "outerHTML"
        
        # Kirim toast peringatan gagal
        payload = {
            "showToast": {"message": "Gagal memperbarui. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class SearchContractView(LoginRequiredMixin, ListView):
    """Search contract by name or date with pagination support."""
    model = Contract
    context_object_name = "contracts"
    template_name = "contract/table-container.html"
    paginate_by = 20  # Sesuaikan dengan paginate_by di ListClientView

    def dispatch(self, request, *args, **kwargs):
        # Tolak jika diakses langsung dari browser tanpa melalui HTMX
        if not request.headers.get('HX-Request'):
            raise Http404("The requested item does not exist.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.GET.get("search", "").strip()
        # contract_date = self.request.GET.get("contract_date", "").strip()
        if query:
            return Contract.objects.filter(
                    Q(client__nama__icontains=query)
                )
        return Contract.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        paginator = page_obj.paginator

        context['custom_page_range'] = paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context
######## End Contract ########


######## Payment ########
class ListPaymentView(LoginRequiredMixin, ListView):
    model = Payment
    context_object_name = "payments"
    template_name = "payment/list.html"
    paginate_by = 20 # Data per page

    def render_to_response(self, context, **response_kwargs):
        """Kembalikan partial container tabel (termasuk pagination) jika request HTMX"""
        if self.request.headers.get("HX-Request") == "true":
            # Kita arahkan ke berkas baru yang membungkus tabel DAN komponen pagination
            return render(self.request, "payment/table-container.html", context)
        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        queryset = Payment.objects.all()
        # Tangkap kedua parameter filter
        pembayaran = self.request.GET.get("pembayaran", "").strip()
        payment_status = self.request.GET.get("payment_status", "").strip()

        # Filter berdasarkan pembayaran jika ada
        if pembayaran:
            queryset = queryset.filter(pembayaran=pembayaran)

        # Filter berdasarkan status kontrak jika ada
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        """Inject payment creation form into the context."""
        context = super().get_context_data(**kwargs)
        context["form"] = PaymentForm
        
        # Gunakan or "" untuk mencegah nilai None masuk ke template
        context['current_pembayaran'] = self.request.GET.get("pembayaran", "").strip()
        context['current_payment_status'] = self.request.GET.get("payment_status", "").strip()

        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context


class CreatePaymentView(LoginRequiredMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = "client/add-modal.html"

    def form_valid(self, form):
        # contract = form.save(commit=False)
        # contract.save()
        form.save()

        # Render kembali form kosong agar siap digunakan untuk penambahan berikutnya
        fresh_form = ContractForm()
        response = render(self.request, "contract/form-fields.html", {"form": fresh_form})
        
        payload = {
            "contractListChanged": {},
            "showToast": {"message": "Kontak berhasil ditambahkan!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang partial form-fields beserta errornya
        response = render(self.request, "contract/form-fields.html", {"form": form})
        
        # Targetkan ulang langsung ke ID form-nya
        response["HX-Retarget"] = "#add-contract-form"
        response["HX-Reswap"] = "outerHTML"
        
        payload = {
            "showToast": {"message": "Gagal menyimpan. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class DeletePaymentView(LoginRequiredMixin, DeleteView):
    model = Contract
    success_url = reverse_lazy("todo_app:contract_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "contractListChanged": {},
                "showToast": {"message": "Kontrak berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response
            
        return super().delete(request, *args, **kwargs)


class EditPaymentView(LoginRequiredMixin, UpdateView):
    model = Contract
    context_object_name = "contract"
    form_class = ContractUpdateForm
    pk_url_kwarg = "pk"
    template_name = "contract/edit-modal.html"

    def get_queryset(self):
        return Contract.objects.all()

    def form_valid(self, form):
        contract = form.save(commit=False)
        contract.save()

        # Kirim HTMX Trigger JSON untuk merefresh daftar & menampilkan toast sukses
        response = HttpResponse("")
        payload = {
            "contractListChanged": {},
            "showToast": {"message": "Kontrak berhasil diperbarui!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang form fields dengan pesan error
        response = render(self.request, "contract/edit-form-fields.html", {"form": form, "contract": self.get_object()})
        
        # Retarget langsung ke ID form edit
        response["HX-Retarget"] = f"#edit-contract-form-{self.get_object().id}"
        response["HX-Reswap"] = "outerHTML"
        
        # Kirim toast peringatan gagal
        payload = {
            "showToast": {"message": "Gagal memperbarui. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class SearchPaymentView(LoginRequiredMixin, ListView):
    model = Payment
    context_object_name = "payments"
    template_name = "payment/table-container.html"
    paginate_by = 20  # Sesuaikan dengan paginate_by di ListClientView

    def dispatch(self, request, *args, **kwargs):
        # Tolak jika diakses langsung dari browser tanpa melalui HTMX
        if not request.headers.get('HX-Request'):
            raise Http404("The requested item does not exist.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.GET.get("search", "").strip()
        # Payment_date = self.request.GET.get("Payment_date", "").strip()
        if query:
            return Payment.objects.filter(
                    Q(client__nama__icontains=query)
                )
        return Contract.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        paginator = page_obj.paginator

        context['custom_page_range'] = paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context
######## End Payment ########


######## Teaching ########
class ListTeachingView(LoginRequiredMixin, ListView):
    """Display a list of tasks for the logged-in user, with optional filtering and HTMX support."""

    model = Teaching
    context_object_name = "teachings"
    template_name = "teaching/list.html"

    def render_to_response(self, context, **response_kwargs):
        """Return partial template if HTMX request, otherwise return full page."""
        if self.request.headers.get("HX-Request") == "true":
            return render(self.request, "teaching/table-rows.html", {"teachings": context["teachings"]})
        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        """Filter tasks by user and query params (completed/uncompleted)."""
        # queryset = Todo.objects.filter(user=self.request.user)
        # value_param = self.request.GET.get("filter")
        # if value_param == "completed":
        #     queryset = queryset.filter(completed=True)
        # elif value_param == "uncompleted":
        #     queryset = queryset.filter(completed=False)
        # return queryset
        return Teaching.objects.all()

    def get_context_data(self, **kwargs):
        """Inject task creation form into the context."""
        context = super().get_context_data(**kwargs)
        context["form"] = TeachingForm
        return context


class SearchTeachingView(LoginRequiredMixin, ListView):
    """Search tasks by title for the current user."""

    model = Teaching
    context_object_name = "teachings"
    template_name = "teaching/table-rows.html"

    def get_queryset(self):
        """Return tasks matching the search query."""
        query = self.request.GET.get("search")
        if query:
            return self.request.user.teachings.filter(Q(title__icontains=query))
        return self.request.user.teachings.all()


class CreateTeachView(LoginRequiredMixin, CreateView):
    """Create a new task and return HTMX partials for success or validation errors."""

    model = Teaching
    form_class = TeachingForm
    template_name = "teaching/add-modal.html"

    def form_valid(self, form):
        """Assign user to task, save it, and return rendered row with success trigger."""
        teaching = form.save(commit=False)
        teaching.save()

        response = render(self.request, "todos/partials/table-row.html", {"teaching": teaching})
        response["HX-Trigger"] = "success"
        return response

    def form_invalid(self, form):
        """Return modal with validation errors and HTMX fail trigger."""
        response = render(self.request, "todos/partials/add-task-modal.html", {"form": form})
        response["HX-Retarget"] = "#add-todo-modal"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger-After-Settle"] = "fail"
        return response


class UpdateTeachingStatusView(LoginRequiredMixin, View):
    """Toggle the completion status of a task (complete/incomplete)."""

    def post(self, request, pk):
        """Toggle task status and return updated row or full page."""
        teaching = get_object_or_404(Teaching, pk=pk)
        teaching.status_teaching = not teaching.status_teaching
        teaching.save()

        if request.headers.get("HX-Request") == "true":
            return render(request, "teaching/table-row.html", {"teaching": teaching})
        teachings = Teaching.objects.all()
        return render(request, "teaching/teaching-list.html", {"teachings": teachings})

    def get(self, request):
        """Block GET requests; only POST is allowed."""
        return HttpResponseNotAllowed(["POST"])
######## End Teaching ########