from django.db import models


class Bib(models.Model):
    """
    A bib is like a collection of homogenius items.

    For example a book "Old Man and the Sea" would be a bib, and it would have
    multiple items (which can be loaned out)
    """
    mms_id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "bib"

    def __str__(self):
        return self.name


class Item(models.Model):
    item_id = models.CharField(max_length=255, primary_key=True)
    description = models.TextField()
    barcode = models.CharField(max_length=255)
    bib = models.ForeignKey(Bib)
    # this could be made into a foreign key, but this table is just caching
    # what's in Alma
    category = models.CharField(max_length=255)

    class Meta:
        db_table = "item"

    def __str__(self):
        return self.description
