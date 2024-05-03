# forms-project

### Installation

#### Python Version
``Python 3.10.10``

#### create virtual environment
``python -m venv env``
#### Activate virtual environment in Linux
``source env/bin/activate``
#### Activate virtual environment in Windows
``.\env\Scripts\activate``

#### install Requirements
``pip install -r requirements.txt``
#### Create .env file and following content in it and don't forget to create PostgreSQL database and user before it.
``DB_USER=YOUR_DB_USERNAME``

``DB_PASSWORD=YOUR_DB_PASSWORD``

``DB_HOST=localhost``

``DB_NAME=YOUR_DB_NAME``

``DB_PORT=5432``

#### Make Administrator Migrations and migrate
``python manage.py makemigrations``

``python manage.py migrate``

#### Create admin user
``python manage.py creatsuperuser``

#### Create admin user
``python manage.py runserver``

#### Goto Page  and login using previously create admin user
``http://127.0.0.1:8000/admin``
``http://127.0.0.1:8000/``


### To create new translation keys
``python manage.py makemessages --all --ignore=env``
``python manage.py compilemessages --ignore=env``
