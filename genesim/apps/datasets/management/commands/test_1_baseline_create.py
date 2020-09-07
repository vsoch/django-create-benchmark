from django.core.management.base import BaseCommand
import os
import sys

import json
import time
import pandas

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


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("genes_json", type=str)
        parser.add_argument("output_file", type=str)
        parser.add_argument("hdf_file", type=str)
 

    def handle(self, *args, **options):

        output_file = options.get("output_file")
        genes_json = options.get("genes_json")
        hdf_file = options.get("hdf_file")

        # Start fresh, delete all genes (also deletes similarities)
        Gene.objects.all().delete()

        # All three inputs are required
        if not output_file or not genes_json or not hdf_file:
            sys.exit(f"genes_json, output_file, and hdf_file are required")
  
        # Similarity scores are required
        if not os.path.exists(genes_json) or not os.path.exists(hdf_file):
            sys.exit(f"hdf file with similiarity scores is required.")

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

        data = load_h5(hdf_file)
        print("Creating similarties...")

        start = time.time()
        for i, name1 in enumerate(data["cosine"].index.tolist()):

            print(f"Parsing gene {i} of {total}...")
            gene1, _ = Gene.objects.get_or_create(systematic_name=name1)
            for name2 in data["cosine"].index.tolist():
                gene2, _ = Gene.objects.get_or_create(systematic_name=name2)

                # Skip null values
                if str(data["cosine"].loc[name1, name2]) == "nan":
                    continue

                # Grab the pvalue and score
                score = round(float(data["cosine"].loc[name1, name2]), 3)
                pvalue = round(float(data["pvals"].loc[name1, name2]), 6)

                # Save diagonal both ways (this is artifically done for the test)
                # We want to test filling in an entire matrix, even if redundant
                GeneSimilarity.objects.get_or_create(
                            gene1=gene1,
                            gene2=gene2,
                            score=score,
                            metric="cosine",
                            pvalue=pvalue,
                )
                GeneSimilarity.objects.get_or_create(
                            gene1=gene2,
                            gene2=gene1,
                            score=score,
                            metric="cosine",
                            pvalue=pvalue,
                )

        env = time.time()
        total = GeneSimilarity.objects.count()
        create_sims_time = end-start
        print(f"Created {total} genes similarities in {create_sims_time} seconds.")

        # Save to output file
        with open(output_file, 'w') as fd:
            fd.writelines("metric,seconds")
            fd.writelines(f"baseline_genes_create,{create_genes_time}")
            fd.writelines(f"baseline_sims_create,{create_sims_time}")
