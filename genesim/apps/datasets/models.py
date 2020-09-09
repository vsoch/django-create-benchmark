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

    class Meta:
        unique_together = (
            "gene1",
            "gene2",
            "metric",
        )
