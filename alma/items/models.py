from django.db import models
from .indexes import ItemIndex

class Item(models.Model):
    item_id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    barcode = models.CharField(max_length=255)
    mms_id = models.CharField(max_length=255)
    # this could be made into a foreign key, but this table is just caching
    # what's in Alma
    category = models.CharField(max_length=255)

    search = ItemIndex()

    class Meta:
        db_table = "item"

    def __str__(self):
        return self.name
