from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.db.models import Q
from django.db import models

class Dataset(models.Model):
    name = models.CharField(max_length=500, null=True, blank=True, unique=True)

    class Meta:
        ordering = ["id"]


class Gene(models.Model):
    systematic_name = models.CharField(
        max_length=50, null=True, blank=True, unique=True
    )
    common_name = models.CharField(max_length=50, null=True, blank=True)

    def get_ranked_similar(self, reverse=False):
        """Given a gene, get a sorted listed from the most to least similar
        """
        if not reverse:
            return GeneSimilarity.objects.filter(
                Q(gene1=self) | Q(gene2=self)
            ).order_by("-score")
        return GeneSimilarity.objects.filter(Q(gene1=self) | Q(gene2=self)).order_by(
            "score"
        )

    def __str__(self):
        return "<%s>" % self.systematic_name


class GeneSimilarity(models.Model):
    """A gene similarity is a similarity metric calculated to compare genes
       based on datasets.
    """

    gene1 = models.ForeignKey(
        Gene, on_delete=models.CASCADE, related_name="gene_similarity1"
    )
    gene2 = models.ForeignKey(
        Gene, on_delete=models.CASCADE, related_name="gene_similarity2"
    )
    metric = models.CharField(max_length=50)
    score = models.DecimalField(max_digits=10, decimal_places=3)
    pvalue = models.DecimalField(max_digits=10, decimal_places=6)

    def save(self, *args, **kwargs):
        """Override the save function to ensure that only one similarity score
           for any pair of genes can be created. If a different ordering is 
           presented, it is fixed and we get an integrity error.
        """
        # Only update order if not in databsase yet, ensure genes ordered by name
        if not self.pk:

            if self.score in [None, "", "nan"]:
                raise FieldError(
                    "score for a gene similarity cannot be a null or empty value."
                )
            # If you wanted to just save the diagonal, you could order the 
            # systematic names here and then it would raise an error


        super(GeneSimilarity, self).save(*args, **kwargs)

    class Meta:
        unique_together = (
            "gene1",
            "gene2",
            "metric",
        )


class Data(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)
    value = models.DecimalField(max_digits=10, decimal_places=3)
    gene = models.ForeignKey(
        "datasets.Gene", null=True, blank=True, on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return "%s - %s" % (self.orf, self.value)
