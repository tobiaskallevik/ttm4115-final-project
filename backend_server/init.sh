#!/bin/bash

set -e

echo "-> Deleting existing database..."
rm -f db.sqlite3

source venv/bin/activate
echo "-> Creating migration files..."
python manage.py makemigrations core
echo "-> Applying migrations..."
python manage.py migrate

echo "-> Populating initial database data..."
cat <<EOF | python manage.py shell
from core.models import Restaurant
from django.contrib.auth.models import User

# 1. Create the dummy restaurant needed for the React frontend
restaurant, created = Restaurant.objects.get_or_create(name="Trondheim Pizzeria")
if created:
    print("Added dummy restaurant: Trondheim Pizzeria (ID: 1)")
else:
    print("Dummy restaurant already exists.")

# 2. Create a superuser for the Django admin panel (username: admin, password: admin)
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin")
    print("Created superuser: admin / admin")
else:
    print("Superuser 'admin' already exists.")
EOF

sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto