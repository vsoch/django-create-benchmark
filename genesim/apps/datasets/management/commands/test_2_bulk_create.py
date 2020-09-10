from django.core.management.base import BaseCommand
import os
import sys

import json
import time
import pandas
import numpy

from genesim.apps.datasets.models import Gene, GeneSimilarity


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

        # Done in groups with update so we don't need to loop through millions
        # of datasets! It will still take some time.
        listing = [Gene(systematic_name=name) for name in genes]
        Gene.objects.bulk_create(listing)
        end = time.time()
        total = Gene.objects.count()

        # metric 1: time to create genes in seconds
        create_genes_time = end - start

        print(f"Created {total} genes in {create_genes_time} seconds.")

        data = create_sims(genes)
        start = time.time()

        # Create diagonals first
        print("Creating diagonals...")
        listing = []
        for i, name1 in enumerate(data.index.tolist()):
            gene1 = Gene.objects.get(systematic_name=name1)
            listing.append(
                GeneSimilarity(gene1=gene1, gene2=gene1, score=1.0, metric="cosine")
            )
        GeneSimilarity.objects.bulk_create(listing)

        print("Creating similarties...")
        for i, name1 in enumerate(data.index.tolist()):

            # Here we will do bulk create on the level of the gene
            print(f"Parsing gene {i} of {total}...")
            gene1 = Gene.objects.get(systematic_name=name1)
            listing = []

            for name2 in data.index.tolist():
                gene2 = Gene.objects.get(systematic_name=name2)

                # Only process when genes equal (similarity 1) or sorted order
                if gene1.systematic_name > gene2.systematic_name or gene1 == gene2:
                    continue

                # Grab the pvalue and score
                score = round(float(data.loc[name1, name2]), 3)

                # Save diagonal both ways (this is artifically done for the test)
                # We want to test filling in an entire matrix, even if redundant
                listing += [
                    GeneSimilarity(
                        gene1=gene1, gene2=gene2, score=score, metric="costine"
                    ),
                    GeneSimilarity(
                        gene1=gene2, gene2=gene1, score=score, metric="costine"
                    ),
                ]

            # Bulk create for the row
            GeneSimilarity.objects.bulk_create(listing)

        end = time.time()
        total_sims = GeneSimilarity.objects.count()
        total_genes = Gene.objects.count()
        create_sims_time = end - start
        print(f"Created {total_sims} genes similarities in {create_sims_time} seconds.")

        # Save to output file
        with open(output_file, "w") as fd:
            fd.writelines("metric,seconds,count\n")
            fd.writelines(f"bulk_create_genes,{create_genes_time},{total_genes}\n")
            fd.writelines(f"bulk_create_sims,{create_sims_time},{total_sims}\n")
