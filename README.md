# Django: create benchmarks

This is a small project to test strategies for running bulk create statements
for a Django app. We would assume that this would be a minimal baseline, meaning that update
statements would take longer. Basically, I have an application that stores similarity scores for genes,
and the creation and update of both the genes and the scores takes an immensely long time using
standard Django queries. We want to benchmark the following:

| name | description | 
|------|-------------|
|baseline| Django create queries |
|bulk | Django bulk_create (likely comparable to bulk insert SQL statements)|
|copyfrom | postgresql COPY with queries |
|copyfromfile | postgresql COPY from file |

For all of the above, the tests should be done with respect to create, and we assume update
would take somewhat longer. Likely the tools
to measure how long it takes will vary (e.g., time on the command line vs the time module
in Python) but I'm anticipating the differences to be large enough to make the tool differences
trivial. I'm using wisdom from [this post](http://stefano.dissegna.me/django-pg-bulk-insert.html)
to not repeat tests that are redundant (e.g., using Django ORM to create vs a cursor that
essentially does the same thing and performs equivalently.

## Similarity Creation

Since we are creating a similarity matrix, we will take the following strategy:

1. create the diagonal entries first
2. iterate over rows and derive pairs (gene1 and gene2) based on gene1's systematic name being less than gene2's systematic name (and not equal). This means that for some pair of gene1 and gene2 where this relationship applies, we create the matrix entry for both `[gene1,gene2]` and `[gene2,gene1]` and when we hit the same pair on the other side of the diagonal, based on the systematic name ordering we won't re-create it.
3. For Django bulk inserts, we will do them on the level of rows since it requires holding the list of objects in memory.

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

This will test the time to create both genes, and the gene similarities (times provided separately).
We use the standard Django ORM, meaning `<Model>.objects.create`.

```bash
/bin/bash benchmarks/test_1_baseline_create.sh
```

We output to a csv file in the same folder, with the same name.

#### 2. bulk create

For this strategy, we use bulk create for all genes, and for each row in the
similarity matrix (all scores for one gene, not repeating across the diagonal).
This means creating a listing of `Gene` or `GeneSimilarity` objects, and then using
`<Model>.objects.bulk_create`.

```bash
/bin/bash benchmarks/test_2_bulk_create.sh
```

The outside standard is the same.

#### 3. COPY from create

This attempt will stream records into queries. For data that we can hold in memory, this means
using StringIO with a csv writer:

```python
# Stream set of queries for one gene1, all matching gene2
stream = StringIO()
writer = csv.writer(stream, delimiter='\t')
```

and then looping through gene ids to create, and writing rows to it:

```python
writer.writerow([gene1.id, gene2.id, 'cosine', score])
```

We do this for diagonals (creating both orderings) and then separately
for ordered genes (only in the case when gene1 is less than gene2 but not equal.
When then providing the entire stream to write to the database:

```python
# Seek to start of stream, run query for row
stream.seek(0)
with closing(connection.cursor()) as cursor:
    cursor.copy_from(
        file=stream,
        table='datasets_genesimilarity',
        sep='\t',
        columns=('gene1_id', 'gene2_id', 'metric', 'score'),
    )
```

The bottleneck here is primarily memory - since we aren't streaming from an actual
file, we rely on StringIO. For genes there is no problem (there are only 6500 that can
fit in memory) and the same for diagonals to the matrix (similarity scores, N=6500).
Where we are limited is with respect to the rest of the similarity scores - we use
a strategy that creates a stream for each row of genes. To run the entire thing,
we do:

```bash
/bin/bash benchmarks/test_3_copyfrom_create.sh
```

#### 4. COPY from file

It dawned on me that a significant portion of the time for test 3 would be querying the
database still in order to derive the StringIO lists of genes! To account for this, 
we do a test that separates the write from the database
query by writing records to file first, and then streaming directly from the file.

```bash
/bin/bash benchmarks/test_4_copyfromfile_create.sh
```

From this we learn that the query itself is speedy, and it's the original looping through
genes that takes ample time.

# 2. Results

The table below shows the name of the metric, time in seconds (or hours) and a description.
For the last set of tests `copyfromwrite_*` we separate the similarity creation into a few parts:

 - writing diagonals using StringIO and copyfrom (`copyfromfile_create_diagonal_sims`)
 - writing all other gene similarity values to file (`copyfromfile_write_genes_file`)
 - streaming directly from this file (`copyfromfile_create_sims`)

The goal is to separate the work of querying the database to derive things to write
from the actual copy from interaction. And in fact we learn that the copy from 
query is extremely fast (23 minutes) and the bottleneck is deriving the original scores / 
putting them in a file to stream (5.90 hours).

| name | time|count    |description | 
|------|-----|---------|------------|
|baseline_create_genes|8.057 seconds|6500 genes| creating genes with Django queries|
|baseline_create_sims|31.28 hours|42250000 similarity scores| creating similarities with Django queries|
|bulk_create_genes|0.253 seconds|6500 genes| creating genes with bulk_create Django query |
|bulk_create_sims|7.28 hours| 42250000 similarity scores | creating similarity scores with bulk_create for each row of genes |
|copyfrom_create_genes|0.056 seconds|6500 genes | creating genes with one copyfrom list|
|copyfrom_create_sims|6.681 hours | 42250000 similarity scores| using copyfrom with StringIO (per row of genes)|
|copyfromfile_create_diagonal_sims|4.66 seconds|6500 diagonal similarities| StringIO and copy from for matrix diagonal|
|copyfromfile_write_genes_file|5.90 hours|42243500 gene similarites (not including diagonals)| writing all other gene sims to a text file|
|copyfromfile_create_genes|0.056 seconds|6500 genes| creating genes with one copyfrom list|
|copyfromfile_create_sims|23.29 minutes|42250000 total gene similarities|creating similiarties with copyfrom directly from file|

Indeed, the operation to write the final scores is speedy! If we can find a fast way to
produce the large file, this seems like a possible solution.

# 3. Automation

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
