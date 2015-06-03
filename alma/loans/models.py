from django.db import models
from django.utils.timezone import now
from alma.alma.api import create_loan, return_loan


class Loan(models.Model):
    """
    This represents a loan to a user. It maps 1:1 with a Loan in alma
    """
    # the actual Loan ID from the Alma API
    loan_id = models.CharField(max_length=255, primary_key=True)
    item = models.ForeignKey('items.Item')
    user = models.ForeignKey("users.User")
    loaned_on = models.DateTimeField(auto_now_add=True)
    returned_on = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = "loan"

    def return_(self):
        """
        Return, checkin, un-loan
        """
        self.returned_on = now()
        return self.save()

    def to_html(self):
        # TODO
        return "foo"

    def save(self, *args, **kwargs):
        """
        Create the loan in Alma or mark it as returned
        """
        if self.returned_on is None:
            # the item is being checked out
            response = create_loan(username=self.user.username, barcode=self.item.barcode)
            self.loan_id = response['loan_id']
        else:
            response = return_loan(mms_id=self.item.bib.pk, item_id=self.item.pk)

        return super().save(*args, **kwargs)
