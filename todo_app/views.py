from django.shortcuts import render, redirect, HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseNotAllowed, Http404, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
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
        Client, Contract, Payment, Teaching, MaterialFile, TeachingRecord
    )
from .forms import (
        ClientForm, TeachingForm, ContractForm, ContractUpdateForm, PaymentForm, TeachingUpdateForm, PaymentUpdateForm,
    )
import json
from dal import autocomplete
from django.utils import timezone
from urllib.parse import quote



# ABOUT = {
#     "profile": {
#         "name": "Sakura Wulandari, S.Pd",
#         "nickname": "Sensei Sakura",
#         "tagline": (
#             "Mengajar bahasa Jepang untuk anak-anak lewat lagu, permainan, dan cerita, "
#             "baik privat maupun di sekolah. Belajar jadi seru, bukan menakutkan!"
#         ),
#         "photo": "",  # isi URL foto, mis. "/media/profile/sensei.jpg". Kosong = tampil kanji 先生
#         "bio": [
#             "Halo! Saya pengajar bahasa Jepang dengan pengalaman lebih dari 6 tahun mengajar "
#             "anak usia 5-15 tahun. Saya percaya anak belajar paling cepat saat mereka merasa senang.",
#             "Setiap pertemuan saya rancang dengan permainan kana, lagu anak Jepang, dan pengenalan "
#             "budaya, sehingga anak tidak hanya hafal kosakata, tetapi juga berani berbicara.",
#         ],
#         "details": [
#             ("Nama lengkap", "Sakura Wulandari, S.Pd"),
#             ("Domisili", "Jakarta, Indonesia"),
#             ("Pendidikan", "S1 Pendidikan Bahasa Jepang"),
#             ("Sertifikasi", "JLPT N2 · Sertifikat Pengajar BIPA/NIHONGO"),
#             ("Bahasa", "Indonesia, Jepang, Inggris"),
#             ("Email", "sensei@example.com"),
#             ("Instagram", "@sensei.sakura"),
#         ],
#         "whatsapp": "6281234567890",  # format internasional tanpa + / 0 di depan
#         "whatsapp_display": "+62 812-3456-7890",
#         "wa_message": "Konnichiwa Sensei! Saya ingin tanya kelas bahasa Jepang untuk anak.",
#     },
#     "stats": [
#         {"value": "6+", "label": "Tahun mengajar"},
#         {"value": "120+", "label": "Murid privat & sekolah"},
#         {"value": "5", "label": "Sekolah mitra"},
#         {"value": "N2", "label": "Sertifikasi JLPT"},
#     ],
#     "programs": [
#         {
#             "icon": "🏠",
#             "title": "Kelas Privat",
#             "badge": "1 guru : 1 murid",
#             "desc": "Materi menyesuaikan kecepatan dan minat anak. Di rumah atau online.",
#             "points": [
#                 "Kurikulum dari hiragana & katakana hingga percakapan dasar",
#                 "Jadwal fleksibel, 60 menit per pertemuan",
#                 "Laporan perkembangan untuk orang tua",
#             ],
#         },
#         {
#             "icon": "🏫",
#             "title": "Mengajar di Sekolah",
#             "badge": "Kelas kelompok",
#             "desc": "Ekstrakurikuler & mata pelajaran bahasa Jepang yang interaktif.",
#             "points": [
#                 "Metode permainan, lagu, dan proyek kelompok",
#                 "Silabus dan penilaian siap pakai untuk sekolah",
#                 "Pengenalan budaya: origami, festival, kuliner",
#             ],
#         },
#     ],
#     "experiences": [
#         {"year": "2023 - sekarang", "title": "Guru Bahasa Jepang (Ekstrakurikuler)",
#          "place": "SD Nusantara Ceria", "desc": "Mengampu 4 kelas, 80+ siswa kelas 3-6."},
#         {"year": "2020 - sekarang", "title": "Pengajar Privat Anak",
#          "place": "Mandiri", "desc": "Membimbing 40+ murid privat usia 5-15 tahun."},
#         {"year": "2019 - 2022", "title": "Instruktur Bahasa Jepang",
#          "place": "Lembaga Kursus Sakura", "desc": "Kelas dasar N5-N4 untuk anak dan remaja."},
#     ],
#     "portfolio": [
#         {"icon": "🏆", "tag": "Prestasi", "year": "2025", "title": "Juara 1 Lomba Pidato Bahasa Jepang Anak",
#          "desc": "Murid binaan meraih juara tingkat provinsi."},
#         {"icon": "🎎", "tag": "Kegiatan", "year": "2024", "title": "Festival Budaya Jepang Sekolah",
#          "desc": "Penampilan lagu, origami, dan kimono untuk 300+ penonton."},
#         {"icon": "📘", "tag": "Karya", "year": "2024", "title": "Buku Aktivitas Kana untuk Anak",
#          "desc": "Lembar mewarnai & latihan menulis hiragana-katakana."},
#         {"icon": "🎓", "tag": "Sertifikasi", "year": "2022", "title": "JLPT N2",
#          "desc": "Japanese-Language Proficiency Test level N2."},
#     ],
#     "testimonials": [
#         {"quote": "Anak saya yang awalnya malu kini rajin latihan menyanyi lagu Jepang di rumah.",
#          "name": "Ibu Rina", "role": "Orang tua murid privat"},
#         {"quote": "Metodenya menyenangkan. Siswa antusias dan nilai ekstrakurikulernya meningkat.",
#          "name": "Bapak Andi", "role": "Kepala SD Nusantara Ceria"},
#         {"quote": "Dalam 3 bulan, anak saya sudah bisa memperkenalkan diri dalam bahasa Jepang.",
#          "name": "Ibu Dewi", "role": "Orang tua murid privat"},
#     ],
# }


# class AboutView(TemplateView):
#     """Halaman publik, sengaja tanpa LoginRequiredMixin agar bisa dibuka pengunjung."""

#     template_name = "about.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update(ABOUT)
#         profile = ABOUT["profile"]
#         # Satu sumber kebenaran untuk tombol WhatsApp & QR code
#         context["wa_url"] = f"https://wa.me/{profile['whatsapp']}?text={quote(profile['wa_message'])}"
#         return context

ABOUT = {
    "profile": {
        "name": "Sakura Wulandari, S.Pd",
        "nickname": "Sensei Sakura",
        "tagline": (
            "Mengajar bahasa Jepang untuk siswa SD hingga SMA dan profesional yang sudah bekerja, "
            "baik privat maupun di sekolah. Materi disesuaikan usia dan tujuan, belajar jadi seru!"
        ),
        "photo": "",  # isi URL foto, mis. "/media/profile/sensei.jpg". Kosong = tampil kanji 先生
        "bio": [
            "Halo! Saya pengajar bahasa Jepang dengan pengalaman lebih dari 6 tahun mengajar "
            "siswa SD, SMP, SMA, hingga karyawan. Saya percaya belajar paling cepat saat kita merasa senang "
            "dan tahu untuk apa kita belajar.",
            "Setiap pertemuan saya rancang sesuai usia: permainan dan lagu untuk anak, latihan JLPT "
            "untuk remaja, serta percakapan kerja untuk profesional, agar semua berani berbicara.",
        ],
        "details": [
            ("Nama lengkap", "Sakura Wulandari, S.Pd"),
            ("Domisili", "Jakarta, Indonesia"),
            ("Pendidikan", "S1 Pendidikan Bahasa Jepang"),
            ("Sertifikasi", "JLPT N2 · Sertifikat Pengajar BIPA/NIHONGO"),
            ("Bahasa", "Indonesia, Jepang, Inggris"),
            ("Email", "sensei@example.com"),
            ("Instagram", "@sensei.sakura"),
        ],
        "whatsapp": "6281234567890",  # format internasional tanpa + / 0 di depan
        "whatsapp_display": "+62 812-3456-7890",
        "wa_message": "Konnichiwa Sensei! Saya ingin tanya kelas bahasa Jepang.",
    },
    "stats": [
        {"value": "6+", "label": "Tahun mengajar"},
        {"value": "120+", "label": "Murid privat & sekolah"},
        {"value": "5", "label": "Sekolah mitra"},
        {"value": "N2", "label": "Sertifikasi JLPT"},
    ],
    "programs": [
        {
            "icon": "🎒", "title": "Kelas SD", "badge": "Fun & Kana", "featured": False,
            "audience": "Siswa SD · usia 6-12 tahun",
            "desc": "Mengenal bahasa Jepang lewat lagu, permainan, dan cerita bergambar.",
            "specs": [
                ("Fokus materi", "Hiragana, katakana, salam, angka, kosakata harian"),
                ("Metode", "Lagu, permainan kartu, origami, mewarnai"),
                ("Format", "Privat di rumah/online atau kelompok di sekolah"),
                ("Durasi", "45 menit · 1-2x seminggu"),
                ("Target", "Bisa membaca kana dan memperkenalkan diri"),
            ],
        },
        {
            "icon": "🎧", "title": "Kelas SMP & SMA", "badge": "Siap JLPT", "featured": True,
            "audience": "Siswa SMP-SMA · usia 12-18 tahun",
            "desc": "Fondasi tata bahasa kuat untuk nilai sekolah, JLPT, dan impian kuliah atau pertukaran pelajar ke Jepang.",
            "specs": [
                ("Fokus materi", "Tata bahasa N5-N4, kanji dasar, percakapan"),
                ("Metode", "Latihan soal, anime & lagu, diskusi, simulasi"),
                ("Format", "Privat/semi-privat atau mata pelajaran/ekskul di sekolah"),
                ("Durasi", "60-90 menit · 1-2x seminggu"),
                ("Target", "Lulus JLPT N5/N4 dan lomba pidato"),
            ],
        },
        {
            "icon": "💼", "title": "Kelas Pekerja & Dewasa", "badge": "Fokus tujuan", "featured": False,
            "audience": "Karyawan & umum · 18+ tahun",
            "desc": "Belajar praktis dan efisien untuk karier, kerja di perusahaan Jepang, atau program magang.",
            "specs": [
                ("Fokus materi", "Percakapan kerja, keigo dasar, kanji, persiapan JLPT"),
                ("Metode", "Roleplay, studi kasus kantor, latihan wawancara"),
                ("Format", "Privat online/offline, jadwal malam atau akhir pekan"),
                ("Durasi", "60-90 menit · 1-3x seminggu"),
                ("Target", "Lulus JLPT N4/N3 dan siap wawancara kerja"),
            ],
        },
    ],
    "experiences": [
        {"year": "2023 - sekarang", "title": "Guru Bahasa Jepang (Ekstrakurikuler)",
         "place": "SD Nusantara Ceria", "desc": "Mengampu 4 kelas, 80+ siswa kelas 3-6."},
        {"year": "2020 - sekarang", "title": "Pengajar Privat Anak",
         "place": "Mandiri", "desc": "Membimbing 40+ murid privat, dari siswa SD hingga pekerja."},
        {"year": "2019 - 2022", "title": "Instruktur Bahasa Jepang",
         "place": "Lembaga Kursus Sakura", "desc": "Kelas dasar N5-N4 untuk anak dan remaja."},
    ],
    "portfolio": [
        {"icon": "🏆", "tag": "Prestasi", "year": "2025", "title": "Juara 1 Lomba Pidato Bahasa Jepang Anak",
         "desc": "Murid binaan meraih juara tingkat provinsi."},
        {"icon": "🎎", "tag": "Kegiatan", "year": "2024", "title": "Festival Budaya Jepang Sekolah",
         "desc": "Penampilan lagu, origami, dan kimono untuk 300+ penonton."},
        {"icon": "📘", "tag": "Karya", "year": "2024", "title": "Buku Aktivitas Kana untuk Anak",
         "desc": "Lembar mewarnai & latihan menulis hiragana-katakana."},
        {"icon": "🎓", "tag": "Sertifikasi", "year": "2022", "title": "JLPT N2",
         "desc": "Japanese-Language Proficiency Test level N2."},
    ],
    "testimonials": [
        {"quote": "Anak saya yang awalnya malu kini rajin latihan menyanyi lagu Jepang di rumah.",
         "name": "Ibu Rina", "role": "Orang tua murid privat"},
        {"quote": "Metodenya menyenangkan. Siswa antusias dan nilai ekstrakurikulernya meningkat.",
         "name": "Bapak Andi", "role": "Kepala SD Nusantara Ceria"},
        {"quote": "Materinya praktis dan langsung terpakai untuk wawancara kerja saya. Lulus JLPT N4!",
         "name": "Dimas", "role": "Karyawan, murid kelas dewasa"},
    ],
}


class AboutView(TemplateView):
    """Halaman publik (tanpa LoginRequiredMixin). Pilih desain lewat ?style=sakura|washi|neon."""

    TEMPLATES = {
        "sakura": "about_sakura.html",  # playful, ramah anak
        "washi": "about_washi.html",    # editorial minimalis, elegan
        "neon": "about_neon.html",      # dark bento, modern
    }
    DEFAULT_STYLE = "sakura"

    def get_template_names(self):
        return [self.TEMPLATES[self._style()]]

    def _style(self):
        style = self.request.GET.get("style", self.DEFAULT_STYLE)
        return style if style in self.TEMPLATES else self.DEFAULT_STYLE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(ABOUT)
        profile = ABOUT["profile"]
        context["style"] = self._style()
        # Satu sumber kebenaran untuk tombol WhatsApp & QR code
        context["wa_url"] = f"https://wa.me/{profile['whatsapp']}?text={quote(profile['wa_message'])}"
        return context

###################################################################################################################################################
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
        client_id = self.forwarded.get('client', None)
        if client_id:
            qs = qs.filter(client_id=client_id)

        if self.q:
            qs = qs.filter(
                Q(client__nama__icontains=self.q) | 
                Q(client__alamat__icontains=self.q) | 
                Q(client__kontak=self.q) |
                Q(kode_kontrak__icontains=self.q)
            )

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
        context["form"] = ClientForm()

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


    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for create data")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()

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

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for delete data")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "clientListChanged": {},
                "showToast": {"message": "Client berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response
            
        return HttpResponseRedirect(self.get_success_url())


class EditClientView(LoginRequiredMixin, UpdateView):
    model = Client
    context_object_name = "client"
    form_class = ClientForm
    pk_url_kwarg = "pk"
    template_name = "client/edit-modal.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for edit data")
            # return HttpResponseRedirect("/client")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Client.objects.all()

    def form_valid(self, form):
        form.save()

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
        context["form"] = ContractForm()
        
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
    template_name = "contract/add-modal.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for create data")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # contract = form.save(commit=False)
        # contract.save()
        form.save()

        response = HttpResponse("")
        
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

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for delete data")
        return super().dispatch(request, *args, **kwargs)

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
            
        return HttpResponseRedirect(self.get_success_url())


class EditContractView(LoginRequiredMixin, UpdateView):
    model = Contract
    context_object_name = "contract"
    form_class = ContractUpdateForm
    pk_url_kwarg = "pk"
    template_name = "contract/edit-modal.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for edit data")
        return super().dispatch(request, *args, **kwargs)

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
        return Payment.objects.all()

    def get_context_data(self, **kwargs):
        """Inject payment creation form into the context."""
        context = super().get_context_data(**kwargs)
        context["form"] = PaymentForm()

        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context


class CreatePaymentView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "payment/add-modal.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for create data")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()

        response = HttpResponse("")
        
        payload = {
            "paymentListChanged": {},
            "showToast": {"message": "Pembayaran berhasil ditambahkan!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang partial form-fields beserta errornya
        response = render(self.request, "payment/form-fields.html", {"form": form})
        
        # Targetkan ulang langsung ke ID form-nya
        response["HX-Retarget"] = "#add-payment-form"
        response["HX-Reswap"] = "outerHTML"
        
        payload = {
            "showToast": {"message": "Gagal menyimpan. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class DeletePaymentView(LoginRequiredMixin, DeleteView):
    model = Payment
    success_url = reverse_lazy("todo_app:payment_list")

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for delete data")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "paymentListChanged": {},
                "showToast": {"message": "Pembayaran berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response
            
        return super().delete(request, *args, **kwargs)


class EditPaymentView(LoginRequiredMixin, UpdateView):
    model = Payment
    context_object_name = "payment"
    form_class = PaymentUpdateForm
    pk_url_kwarg = "pk"
    template_name = "payment/edit-modal.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for edit data")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Payment.objects.all()

    def form_valid(self, form):
        payment = form.save(commit=False)
        payment.save()

        # Kirim HTMX Trigger JSON untuk merefresh daftar & menampilkan toast sukses
        response = HttpResponse("")
        payload = {
            "paymentListChanged": {},
            "showToast": {"message": "Pembayaran berhasil diperbarui!", "type": "alert-success"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang form fields dengan pesan error
        response = render(self.request, "payment/edit-form-fields.html", {"form": form, "payment": self.get_object()})
        
        # Retarget langsung ke ID form edit
        response["HX-Retarget"] = f"#edit-payment-form-{self.get_object().id}"
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
        if query:
            if query.startswith("::"):
                month = query[2:].strip()
                if month.isdigit() and 1 <= int(month) <= 12:
                    return Payment.objects.filter(tanggal__month=int(month))
                return Payment.objects.none()  # bulan tidak valid -> hasil kosong, bukan error 500
            return Payment.objects.filter(
                    Q(contract__client__nama__icontains=query) |
                    Q(kode_payment__icontains=query)
                )
        return Payment.objects.all()

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
    paginate_by = 20

    def render_to_response(self, context, **response_kwargs):
        """Return partial template if HTMX request, otherwise return full page."""
        if self.request.headers.get("HX-Request") == "true":
            return render(self.request, "teaching/table-container.html", context)
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
        context["form"] = TeachingForm()
        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context


class CreateTeachingView(LoginRequiredMixin, CreateView):
    """Create a new task and return HTMX partials for success or validation errors."""
    model = Teaching
    form_class = TeachingForm
    template_name = "teaching/add-modal.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for create data")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Assign user to task, save it, and return rendered row with success trigger."""
        # teaching = form.save(commit=False)

        # teaching.save()
        form.save()

        # Modal dimuat dinamis ke #dialog-container dan form menarget #add-teach-modal
        # (outerHTML). Response kosong = modal dihapus dari DOM.
        response = HttpResponse("")

        payload = {
            "teachingListChanged": {},
            "showToast": {"message": "Jadwal berhasil ditambahkan!", "type": "alert-success"}
        }
        response['HX-Trigger'] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        """Return modal with validation errors and HTMX fail trigger."""
        response = render(self.request, "teaching/form-fields.html", {"form": form})
        response["HX-Retarget"] = "#add-teach-form"
        response["HX-Reswap"] = "outerHTML"
        payload = {
            "showToast": {"message": "Gagal menyimpan. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class DeleteTeachingView(LoginRequiredMixin, DeleteView):
    model = Teaching
    success_url = reverse_lazy("todo_app:teaching_list")

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for delete data")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "teachingListChanged": {},
                "showToast": {"message": "Jadwal berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response
            
        return HttpResponseRedirect(self.get_success_url())


class EditTeachingView(LoginRequiredMixin, UpdateView):
    model = Teaching
    context_object_name = "teaching"
    # form_class = TeachingForm1
    form_class = TeachingUpdateForm
    pk_url_kwarg = "pk"
    template_name = "teaching/edit-modal.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for edit data")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Teaching.objects.all()

    def form_valid(self, form):
        # teaching = form.save(commit=False)
        # teaching.save()
        form.save()
        
        # Kirim HTMX Trigger JSON untuk merefresh daftar & menampilkan toast sukses
        response = HttpResponse("")

        # fresh_form = TeachingForm()
        # response = render(self.request, "teaching/form-fields.html", {"form": fresh_form})

        payload = {
            "teachingListChanged": {},
            "showToast": {"message": "Jadwal berhasil diperbarui!", "type": "alert-success"}
        }
        #response["HX-Refresh"] = "true"
        response["HX-Trigger"] = json.dumps(payload)
        return response

    def form_invalid(self, form):
        # Render ulang form fields dengan pesan error
        response = render(self.request, "teaching/edit-form-fields.html", {"form": form, "teaching": self.get_object()})
        
        # Retarget langsung ke ID form edit
        response["HX-Retarget"] = f"#edit-teach-form-{self.get_object().id}"
        response["HX-Reswap"] = "outerHTML"
        
        # Kirim toast peringatan gagal
        payload = {
            "showToast": {"message": "Gagal memperbarui. Periksa kembali inputan Anda.", "type": "alert-error"}
        }
        response["HX-Trigger"] = json.dumps(payload)
        return response


class SearchTeachingView(LoginRequiredMixin, ListView):
    """Search tasks by title for the current user."""

    model = Teaching
    context_object_name = "teachings"
    template_name = "teaching/table-container.html"
    paginate_by = 20  # Sesuaikan dengan paginate_by di ListClientView

    def dispatch(self, request, *args, **kwargs):
        # Tolak jika diakses langsung dari browser tanpa melalui HTMX
        if not request.headers.get('HX-Request'):
            raise Http404("The requested item does not exist.")
        return super().dispatch(request, *args, **kwargs)


    def get_queryset(self):
        query = self.request.GET.get("search", "").strip()

        if not query:
            return Teaching.objects.all()

        # 1. Filter khusus jika query diawali "::jam=" (contoh: "::jam=2" atau "::jam=14")
        if query.lower().startswith("::jam="):
            try:
                # Mengambil angka setelah tanda '='
                jam_val = int(query.split("=")[1].strip())
                
                # Validasi rentang jam 0 sampai 23
                if 0 <= jam_val <= 23:
                    # Filter start_time berdasarkan komponen jam saja (jam_val:00 - jam_val:59)
                    return Teaching.objects.filter(start_time__hour=jam_val)
            except (ValueError, IndexError):
                return Teaching.objects.none()

        # 2. Pemetaan nama hari (Bahasa Indonesia & Inggris) ke nilai integer day_of_week (0-6)
        DAY_MAPPING = {
            "senin": 0, "monday": 0, "mon": 0,
            "selasa": 1, "tuesday": 1, "tue": 1,
            "rabu": 2, "wednesday": 2, "wed": 2,
            "kamis": 3, "thursday": 3, "thu": 3,
            "jumat": 4, "jum'at": 4, "friday": 4, "fri": 4,
            "sabtu": 5, "saturday": 5, "sat": 5,
            "minggu": 6, "sunday": 6, "sun": 6,
        }

        # Filter pencarian umum (Client, Kode Kontrak, Waktu biasa)
        filters = Q(client__nama__icontains=query) | \
                  Q(client__kontak__icontains=query) | \
                  Q(kontrak__kode_kontrak__icontains=query) | \
                  Q(start_time__icontains=query)

        # Cek jika query berupa nama hari
        query_lower = query.lower()
        if query_lower in DAY_MAPPING:
            filters |= Q(day_of_week=DAY_MAPPING[query_lower])

        # Cek jika query berupa angka 0-6 langsung untuk day_of_week
        elif query.isdigit() and 0 <= int(query) <= 6:
            filters |= Q(day_of_week=int(query))

        return Teaching.objects.filter(filters).distinct()

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


## Class buat fungsi post yg di modal jadwal
class RecordTeachingView(LoginRequiredMixin, View):
    paginate_by = 20

    def get_context_data(self, teaching, request, **kwargs):
        page_number = request.GET.get("page") or request.POST.get("page") or 1
        
        queryset = Teaching.objects.all()
        paginator = Paginator(queryset, self.paginate_by)
        page_obj = paginator.get_page(page_number)
        
        object_list = list(page_obj.object_list)
        counter0 = object_list.index(teaching) if teaching in object_list else 0

        custom_page_range = paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )

        # Format waktu lokal sekarang untuk default datetime-local input (YYYY-MM-DDTHH:MM)
        now_iso = timezone.localtime(timezone.now()).strftime('%Y-%m-%dT%H:%M')

        context = {
            "teaching": teaching,
            "page_obj": page_obj,
            "forloop": {"counter0": counter0},
            "custom_page_range": custom_page_range,
            "now_iso": now_iso,

        }
        context.update(kwargs)
        return context

    def get(self, request, pk):
        teaching = get_object_or_404(Teaching, pk=pk)
        context = self.get_context_data(teaching=teaching, request=request)
        return render(request, "teaching/record-modal.html", context)

    def post(self, request, pk):
        teaching = get_object_or_404(Teaching, pk=pk)
        kontrak = teaching.kontrak

        if kontrak.contract_status != "Berjalan":
            payload = {
                "showToast": {"message": "Gagal! Kontrak ini sudah selesai atau habis.", "type": "alert-error"}
            }
        else:
            materi = request.POST.get("materi_realisasi", teaching.materi)
            is_rescheduled = request.POST.get("is_rescheduled") == "on"
            
            # Ambil input tanggal pelaksanaan dari form (jika kosong, gunakan waktu sekarang)
            input_tanggal = request.POST.get("tanggal_pelaksanaan")
            tanggal_valid = True
            if input_tanggal:
                # Konversi string datetime-local HTML ke datetime object yang sadar zona waktu (timezone-aware)
                try:
                    naive_dt = timezone.datetime.fromisoformat(input_tanggal)
                    tanggal_pelaksanaan = timezone.make_aware(naive_dt, timezone.get_current_timezone())
                except ValueError:  # format salah, atau sudah mengandung offset zona waktu
                    tanggal_valid = False
            else:
                tanggal_pelaksanaan = timezone.now()

            if not tanggal_valid:
                payload = {
                    "showToast": {"message": "Gagal! Format tanggal pelaksanaan tidak valid.", "type": "alert-error"}
                }
            elif kontrak.tipe_kontrak == "Privat":
                if kontrak.total_pertemuan and kontrak.total_mengajar >= kontrak.total_pertemuan:
                    payload = {
                        "showToast": {"message": "Gagal! Kuota pertemuan kontrak Privat sudah terpenuhi.", "type": "alert-warning"}
                    }
                else:
                    TeachingRecord.objects.create(
                        kontrak=kontrak,
                        teaching=teaching,
                        tanggal_pelaksanaan=tanggal_pelaksanaan,  # Simpan tanggal pilihan user
                        materi_realisasi=materi,
                        is_rescheduled=is_rescheduled
                    )
                    kontrak.check_and_update_status()
                    payload = {
                        "teachingListChanged": {},
                        "showToast": {"message": "Sesi mengajar Privat berhasil dicatat!", "type": "alert-success"}
                    }

            elif kontrak.tipe_kontrak == "Institusi":
                TeachingRecord.objects.create(
                    kontrak=kontrak,
                    teaching=teaching,
                    tanggal_pelaksanaan=tanggal_pelaksanaan,  # Simpan tanggal pilihan user
                    materi_realisasi=materi,
                    is_rescheduled=is_rescheduled
                )
                payload = {
                    "teachingListChanged": {},
                    "showToast": {"message": "Sesi mengajar Institusi berhasil dicatat!", "type": "alert-success"}
                }
            else:
                payload = {
                    "showToast": {"message": "Tipe kontrak tidak dikenali.", "type": "alert-error"}
                }
                
        response = HttpResponse("")
        response["HX-Trigger"] = json.dumps(payload)
        return response


class ListTeachingRecordView(LoginRequiredMixin, ListView):
    model = TeachingRecord
    context_object_name = "teaching_records"
    template_name = "teaching/record-list.html"
    paginate_by = 20

    def render_to_response(self, context, **response_kwargs):
        """Return partial template if HTMX request, otherwise return full page."""
        if self.request.headers.get("HX-Request") == "true":
            return render(self.request, "teaching/record-table-container.html", context)
        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        return TeachingRecord.objects.all()

    def get_context_data(self, **kwargs):
        """Inject task creation form into the context."""
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context


class DeleteTeachingRecordView(LoginRequiredMixin, DeleteView):
    """Menghapus record mengajar yang salah input dan mengembalikan kuota/progres kontrak."""
    model = TeachingRecord
    success_url = reverse_lazy("todo_app:teaching_record_list")

    def dispatch(self, request, *args, **kwargs):
        # Check if the request is from htmx
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("Bad request for delete data")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        teaching_obj = self.object.teaching # Simpan referensi teaching untuk refresh baris jika diperlukan
        
        # Eksekusi delete (method delete() model di atas akan otomatis mereset status kontrak)
        self.object.delete()

        if request.headers.get("HX-Request") == "true":
            response = HttpResponse("")
            payload = {
                "RecordTeachingListChanged": {}, # Trigger untuk merefresh list/tabel jadwal utama jika perlu
                "showToast": {"message": "Sesi mengajar yang salah berhasil dihapus!", "type": "alert-warning"}
            }
            response["HX-Trigger"] = json.dumps(payload)
            return response

        # return super().delete(request, *args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class SearchTeachingRecordView(LoginRequiredMixin, ListView):
    """Cari data record mengajar (TeachingRecord). Format query sama seperti SearchTeachingView.
 
    Format khusus:
      ::jam=14        -> filter berdasarkan jam mulai jadwal (teaching__start_time__hour)
      ::jadwal=senin  -> filter berdasarkan hari JADWAL (teaching__day_of_week);
                         menerima nama hari (ID/EN) atau angka 0-6
      senin           -> (tanpa prefix) filter berdasarkan hari PELAKSANAAN,
                         yaitu hari dari tanggal_pelaksanaan; menerima nama hari
                         (ID/EN) atau angka 0-6 (0 = Senin)
    """
 
    model = TeachingRecord
    context_object_name = "teaching_records"
    template_name = "teaching/record-table-container.html"
    paginate_by = 20
 
    # Pemetaan nama hari (Bahasa Indonesia & Inggris) ke nilai integer day_of_week (0-6)
    DAY_MAPPING = {
        "senin": 0, "monday": 0, "mon": 0,
        "selasa": 1, "tuesday": 1, "tue": 1,
        "rabu": 2, "wednesday": 2, "wed": 2,
        "kamis": 3, "thursday": 3, "thu": 3,
        "jumat": 4, "jum'at": 4, "friday": 4, "fri": 4,
        "sabtu": 5, "saturday": 5, "sat": 5,
        "minggu": 6, "sunday": 6, "sun": 6,
    }
 
    def dispatch(self, request, *args, **kwargs):
        # Tolak jika diakses langsung dari browser tanpa melalui HTMX
        if not request.headers.get('HX-Request'):
            raise Http404("The requested item does not exist.")
        return super().dispatch(request, *args, **kwargs)
 
    def get_queryset(self):
        queryset = TeachingRecord.objects.select_related("teaching__client", "kontrak")
        query = self.request.GET.get("search", "").strip()
 
        if not query:
            return queryset
 
        query_lower = query.lower()
 
        # 1. Filter khusus "::jam=" (contoh: "::jam=2" atau "::jam=14")
        if query_lower.startswith("::jam="):
            try:
                jam_val = int(query.split("=", 1)[1].strip())
            except ValueError:
                return queryset.none()
            if 0 <= jam_val <= 23:
                return queryset.filter(teaching__start_time__hour=jam_val)
            return queryset.none()
 
        # 2. Filter khusus "::jadwal=" (contoh: "::jadwal=senin" atau "::jadwal=0")
        if query_lower.startswith("::jadwal="):
            value = query.split("=", 1)[1].strip().lower()
            if value in self.DAY_MAPPING:
                day = self.DAY_MAPPING[value]
            elif value.isdigit() and 0 <= int(value) <= 6:
                day = int(value)
            else:
                return queryset.none()
            return queryset.filter(teaching__day_of_week=day)
 
        # 3. Filter pencarian umum (Client, Kode Kontrak, Waktu biasa)
        filters = Q(teaching__client__nama__icontains=query) | \
                  Q(teaching__client__kontak__icontains=query) | \
                  Q(kontrak__kode_kontrak__icontains=query) | \
                  Q(teaching__start_time__icontains=query)
 
        # Query berupa nama hari / angka 0-6 -> hari dari tanggal_pelaksanaan.
        # DAY_MAPPING: 0 = Senin ... 6 = Minggu, sedangkan __iso_week_day: 1 = Senin ... 7 = Minggu.
        if query_lower in self.DAY_MAPPING:
            filters |= Q(tanggal_pelaksanaan__iso_week_day=self.DAY_MAPPING[query_lower] + 1)
        elif query.isdigit() and 0 <= int(query) <= 6:
            filters |= Q(tanggal_pelaksanaan__iso_week_day=int(query) + 1)
 
        return queryset.filter(filters)
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        context['custom_page_range'] = page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        )
        return context

######## End Teaching ########