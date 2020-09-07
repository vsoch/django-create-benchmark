# Django: create and update Benchmarks

This is a small project to test strategies for running bulk create and update statements
for a Django app. Basically, I have an application that stores similarity scores for genes,
and the creation and update of both the genes and the scores takes an immensely long time using
standard Django queries. We want to benchmark the following:

| name | description | 
|------|-------------|
|baseline| Django create and queries |
|bulk | Django bulk_create and bulk_update |
|psycopg2 | bulk insert SQL statement |
| csv | postgresql COPY |
|drop | insert all updated records into a new table, drop the old table and rename new table to old one (in one transaction)  |

For all of the above, the tests should be done with respect to create and update. Likely the tools
to measure how long it takes will vary (e.g., time on the command line vs the time module
in Python) but I'm anticipating the differences to be large enough to make the tool differences
trivial.

## Intended Outcome

We are setting up the example to run locally using a dockerized
postgres database, and an application running from a Python virtual environment.
We take on this setup because the intended outcome would be:

 1. deployment on Google Cloud App Engine
 2. using managed SQL in Google Cloud
 3. Batch creates / updates automated by the application

Thus, the higher level goals include two steps:

 1. **Benchmarks**: optimizing the create and update queries
 2. **Automation**: Automating them to be triggered by the Django App Engine application


## Setup

### Configuration

Copy the dummy environment file to an environment file:

```bash
cp .dummy-env .env
```
And then update the postgres credentials to be whatever you like. Other than that, the only environment variable we need to export (at least for local usage) is a secret key used to secure your server. You can use the [secret key generator](https://djecrety.ir/) to make a new secret key, and also export it as the `DJANGO_SECRET_KEY` in your `.dummy-env` file:

```bash
export DJANGO_SECRET_KEY=123455
```
Make sure to source this file when you are done.

```bash
source .env
```

### Docker

To start the docker compose application (your postgres container), you can do the following:

```bash
docker-compose up -d
```
The container also uses the `.env` file so it knows the same secrets as the application. We would
normally containerize both the database and the web server, but since we ultimately want to use
app engine, we don't want to do that.

### Virtual Environment

Let's first make a virtual environment.

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

And then whenever you interact with the application you should use this environment in the future.

### Database

Once you have sourced the virtual environment, create the database and collect static.

```bash
$ make collect
$ make migrations
python manage.py makemigrations
No changes detected
python manage.py makemigrations datasets
Migrations for 'datasets':
  genesim/apps/datasets/migrations/0001_initial.py
    - Create model Dataset
    - Create model Gene
    - Create model Data
    - Create model GeneSimilarity
    - Create model DatasetSimilarity
```
```bash
$ make migrate
python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, datasets, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying datasets.0001_initial... OK
  Applying sessions.0001_initial... OK
```

# 1. Benchmarks

Next, let's run the benchmarks! Each test corresponds with a script in [benchmarks](benchmarks) will output
a result to a text file in the same folder with the same name. You should run all tests from
the root of the repository. You'll need data in [data](data) which I'm not providing in the repository,
but is available on request.

#### 1. baseline create

This will test the time to create both genes, and the gene similarities (times provided separately)

```bash
/bin/bash benchmarks/test_1_baseline_create.sh
```

We output to a csv file in the same folder, with the same name.

#### 2. bulk create

**under development**


# 2. Automation

Automation will first be reliant on setting something up on app engine, so here are instructions for that.

### App Engine

You will want to follow the instructions [here](https://cloud.google.com/appengine/docs/standard/python3/building-app/writing-web-service)
and:

 - create a Google Cloud Project.
 - install the gcloud command line client and Python3+
 - authenticate on the command line with `gcloud auth application-default login`

For example, after I've created my project and I've installed gcloud, I might login and
then set the default project to be my new project:

```bash
$ gcloud auth application-default login
$ gcloud config set project <myproject>
```

On the [Google Project Console](https://console.developers.google.com/apis) you'll want to enable
APIs for:

 - Identity and Access Management (IAM) API
 - Google Storage
