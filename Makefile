.PHONY: collect migrate migrations

# target: collect - calls the "collectstatic" django command
collect:
	python manage.py collectstatic --noinput

migrations: 
	python manage.py makemigrations
	python manage.py makemigrations datasets

migrate: 
	python manage.py migrate

run: 
	python manage.py runserver
