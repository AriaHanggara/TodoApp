from faker import Faker
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import Client, Contract
from .views import generate_unique_username


def create_dummy_client():
	fake = Faker(['en_US', 'fr_FR'])
	phone_numbers = [fake.unique["en_US"].phone_number() for i in range(500)]
	names = [fake.unique["en_US"].name() for i in range(500)]
	addreses = [fake.unique["en_US"].address() for i in range(500)]

	for i in enumerate(names):
		new_user = User.objects.create_user(
	            username=generate_unique_username(i[1]),
	            password='Alhamdulillah123',
	        )

		a, created = Client.objects.get_or_create(
			account_client = new_user,
			nama = i[1],
			kontak = phone_numbers[i[0]],
			alamat = addreses[i[0]]
			)
		print(a)