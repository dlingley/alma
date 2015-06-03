from elasticsearch_dsl import analyzer, tokenizer, token_filter
from elasticmodels import Index, StringField
from .models import Item, Bib

# override the default analyzer for ES to use an ngram filter that breaks words using
# the standard tokenizer. Allow words to be broken up with underscores
custom_analyzer = analyzer(
    "default",
    # the standard analyzer splits the words nicely by default
    tokenizer=tokenizer("standard"),
    filter=[
        # technically, the standard filter doesn't do anything but we include
        # it anyway just in case ES decides to make use of it
        "standard",
        # unfortunately, underscores are not used to break up words with the
        # standard tokenizer, so we do it ourselves
        token_filter(
            "underscore",
            type="pattern_capture",
            patterns=["([^_]+)"],
        ),
        # obviously, lowercasing the tokens is a good thing
        "lowercase",
        # ngram it up. Might want to change from an edge ngram to just an ngram
        token_filter(
            "simple_edge",
            type="edgeNGram",
            min_gram=2,
            max_gram=3
        )
    ]
)


class BibIndex(Index):
    mms_id = StringField(analyzer="keyword")

    class Meta:
        model = Bib
        doc_type = "bib"
        fields = [
            "name"
        ]


class ItemIndex(Index):
    item_id = StringField(analyzer="keyword")
    barcode = StringField(analyzer="keyword")
    # we have to use the custom_analyzer on at least one field, so
    # Elasticsearch-dsl knows about it. Because it becomes the default
    # analyzer, we don't have to use the analyizer elsewhere
    name = StringField(analyzer=custom_analyzer)

    def get_queryset(self, **kwargs):
        return super().get_queryset().select_related("bib")

    class Meta:
        doc_type = "item"
        fields = [
            "description",
            "category",
        ]
        model = Item

    def prepare_name(self, instance):
        return instance.bib.name
