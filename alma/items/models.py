from django.db import models

class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    barcode = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "item"
