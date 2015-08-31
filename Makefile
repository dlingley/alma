.PHONY: run install clean coverage reload

PROJECT_NAME = alma
VENV_DIR ?= .env
# centos puts pg_config in weird places. We run postgres 9.1 and 9.3 in prod and dev
# respectively.
PG_DIRS = /usr/pgsql-9.1/bin:/usr/pgsql-9.3/bin

PYTHON = python3
MANAGE = python manage.py
HOST ?= 0.0.0.0
PORT ?= 8000

export PATH:=$(VENV_DIR)/bin:$(PATH):$(PG_DIRS)

run:
	$(MANAGE) runserver $(HOST):$(PORT)

init:
	rm -rf $(VENV_DIR)
	@$(MAKE) $(VENV_DIR)
	dropdb --if-exists $(PROJECT_NAME)
	createdb $(PROJECT_NAME)
	$(MANAGE) migrate
	$(MANAGE) check
	# create a dummy user
	$(MANAGE) loaddata dummy_user.json

clean:
	find . -iname "*.pyc" -delete
	find . -iname "*.pyo" -delete
	find . -iname "__pycache__" -delete

coverage:
	coverage run $(MANAGE) test && coverage html

test:
	$(MANAGE) test --keepdb && flake8 && isort -rc --diff --check-only $(PROJECT_NAME)

reload:
	$(MANAGE) migrate
	$(MANAGE) collectstatic --noinput
	touch $(PROJECT_NAME)/wsgi.py

$(VENV_DIR):
	$(PYTHON) -m venv .env
	curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | python
	pip install -r requirements.txt
