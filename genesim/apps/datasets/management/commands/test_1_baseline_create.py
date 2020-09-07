from django.core.management.base import BaseCommand
import os
import sys

import json
import time
import pandas
import numpy

from genesim.apps.datasets.models import Gene, GeneSimilarity

def load_h5(file_path, verbose=True):

    output = {}

    with pandas.HDFStore(file_path) as store:
        ks = store.keys()

    for k in ks:
        k = k.lstrip("\/")
        if verbose:
            print(k)
        output[k] = pandas.read_hdf(file_path, k)

    return output


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

        with open(genes_json, 'r') as fd:
            genes = json.loads(fd.read())

        print(f"Creating {len(genes)} genes...")
        start = time.time()

        # Done in groups with update so we don't need to loop through millions
        # of datasets! It will still take some time.
        for name in genes:
            gene, created = Gene.objects.get_or_create(systematic_name=name)
        end = time.time()
        total = Gene.objects.count()

        # metric 1: time to create genes in seconds
        create_genes_time = end-start

        print(f"Created {total} genes in {create_genes_time} seconds.")

        data = create_sims(genes)
        print("Creating similarties...")

        import IPython
        IPython.embed()

        start = time.time()
        for i, name1 in enumerate(data.index.tolist()):

            print(f"Parsing gene {i} of {total}...")
            gene1, _ = Gene.objects.get_or_create(systematic_name=name1)
            for name2 in data.index.tolist():
                gene2, _ = Gene.objects.get_or_create(systematic_name=name2)

                # Grab the pvalue and score
                score = round(float(data.loc[name1, name2]), 3)

                # Save diagonal both ways (this is artifically done for the test)
                # We want to test filling in an entire matrix, even if redundant
                GeneSimilarity.objects.get_or_create(
                            gene1=gene1,
                            gene2=gene2,
                            score=score,
                            metric="cosine", # not really cosine :)
                )
                GeneSimilarity.objects.get_or_create(
                            gene1=gene2,
                            gene2=gene1,
                            score=score,
                            metric="cosine",
                )

        env = time.time()
        total = GeneSimilarity.objects.count()
        create_sims_time = end-start
        print(f"Created {total} genes similarities in {create_sims_time} seconds.")

        # Save to output file
        with open(output_file, 'w') as fd:
            fd.writelines("metric,seconds")
            fd.writelines(f"baseline_create_genes,{create_genes_time}")
            fd.writelines(f"baseline_create_sims,{create_sims_time}")
