from django.db.models import Manager


class ImpotentManager(Manager):
    def delete(self, *args, **kwargs):
        raise RuntimeError("You need to call the delete() method on each object in the queryset")
