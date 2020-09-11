from django.core.management.base import BaseCommand
import os
import sys

import json
import time
import pandas
import numpy

from genesim.apps.datasets.models import Gene, GeneSimilarity

from contextlib import closing
import csv
from io import StringIO

from django.db import connection
from django.utils import timezone


def create_sims(genes):
    """Create a random matrix of values, they aren't actually similarity values
    """
    # Create a random valued matrix
    matrix = numpy.random.randn(len(genes), len(genes))

    # Create a pandas data frame for fake similarity scores
    df = pandas.DataFrame(matrix)

    # Add labels - these of course are wrong because they should mirror
    df.index = genes
    df.columns = genes
    return df


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("genes_json", type=str)
        parser.add_argument("output_file", type=str)

    def handle(self, *args, **options):

        output_file = options.get("output_file")
        genes_json = options.get("genes_json")

        # Start fresh, delete all genes (also deletes similarities)
        Gene.objects.all().delete()

        import IPython
        IPython.embed()

        # All three inputs are required
        if not output_file or not genes_json:
            sys.exit(f"genes_json, and output_file are required")

        # Similarity scores are required
        if not os.path.exists(genes_json):
            sys.exit(f"genes.json is required.")

        with open(genes_json, "r") as fd:
            genes = json.loads(fd.read())

        print(f"Creating {len(genes)} genes...")
        start = time.time()

        # Create stream (to write names)
        stream = StringIO()
        writer = csv.writer(stream, delimiter='\t')
        for i, gene in enumerate(genes):
            writer.writerow([gene, gene])
        stream.seek(0)

        # Write genes from csv stream
        with closing(connection.cursor()) as cursor:
            cursor.copy_from(
                file=stream,
                table='datasets_gene',
                sep='\t',
                columns=('systematic_name', 'common_name'),
            )
        end = time.time()
        total = Gene.objects.count()

        # metric 1: time to create genes in seconds
        create_genes_time = end - start

        print(f"Created {total} genes in {create_genes_time} seconds.")

        data = create_sims(genes)
        start_diagonal_genes = time.time()

        # Create diagonals first
        print("Creating diagonals...")

        stream = StringIO()
        writer = csv.writer(stream, delimiter='\t')
        for i, name1 in enumerate(data.index.tolist()):
            gene1 = Gene.objects.get(systematic_name=name1)
            writer.writerow([gene1.id, gene1.id, 'cosine', 1.0])
        stream.seek(0)

        # Write genes from csv stream
        with closing(connection.cursor()) as cursor:
            cursor.copy_from(
                file=stream,
                table='datasets_genesimilarity',
                sep='\t',
                columns=('gene1_id', 'gene2_id', 'metric', 'score'),
            )

        end_diagonal_genes = time.time()
        time_diagonal_genes = end_diagonal_genes - start_diagonal_genes

        print("Writing to file...")
        start_write = time.time()
        _, tmpfile = tempfile.mkstemp()

        with open(tmpfile, "w") as csv_file:
            writer = csv.writer(csv_file, delimiter='\t')
            for i, name1 in enumerate(data.index.tolist()):
                gene1 = Gene.objects.get(systematic_name=name1)
                for name2 in data.index.tolist():
                    gene2 = Gene.objects.get(systematic_name=name2)

                    # Only process when genes equal (similarity 1) or sorted order
                    if gene1.systematic_name > gene2.systematic_name or gene1 == gene2:
                        continue

                    # Grab the pvalue and score
                    score = round(float(data.loc[name1, name2]), 3)
                    writer.writerow([gene1.id, gene2.id, 'cosine', score])
                    writer.writerow([gene2.id, gene1.id, 'cosine', score])

        end_write = time.time()
        time_write = end_write - start_write

        print("Creating similarties...")
        create_start = time.time()
        with open(tmpfile, 'r') as stream:        
            with closing(connection.cursor()) as cursor:
                cursor.copy_from(
                    file=stream,
                    table='datasets_genesimilarity',
                    sep='\t',
                    columns=('gene1_id', 'gene2_id', 'metric', 'score'),
                )

        create_end = time.time()
        total_sims = GeneSimilarity.objects.count()
        total_genes = Gene.objects.count()
        create_sims_time = create_end - create_start
        print(f"Created {total_sims} genes similarities in {create_sims_time} seconds.")

        # Genes minus diagonal sims
        other_genes = (total_genes * total_genes) - diagonal_sims

        # Save to output file
        with open(output_file, "w") as fd:
            fd.writelines("metric,seconds,count\n")
            fd.writelines(f"copyfromfile_create_diagonal_sims,{time_diagonal_genes},{diagonal_sims}\n")
            fd.writelines(f"copyfromfile_write_genes_file,{time_write},{other_genes}\n")
            fd.writelines(f"copyfromfile_create_genes,{create_genes_time},{total_genes}\n")
            fd.writelines(f"copyfromfile_create_sims,{create_sims_time},{total_sims}\n")
