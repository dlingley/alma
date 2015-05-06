from elasticmodels import Index, StringField

class ItemIndex(Index):
    class Meta:
        doc_type = "item"
        fields = [
            "item_id",
            "name",
            "description",
            "barcode",
            "mms_id",
            "category",
        ]
