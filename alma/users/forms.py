from django import forms

from .models import User


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
        )

    def __init__(self, *args, user, **kwargs):
        """
        `user` is the person using the form, not the person the form is actually going edit
        """
        super().__init__(*args, **kwargs)

        # add a password field to the form if the user is being created. This
        # allows an admin to set an initial password
        if self.instance.pk is None:
            self.fields['password'] = forms.CharField(widget=forms.widgets.PasswordInput)

        if user.pk == self.instance.pk:
            # these fields you shouldn't be allowed to alter if you're editing
            # yourself, for safety reasons
            self.fields.pop("is_active")
            self.fields.pop("is_staff")

        if not user.is_staff:
            # only staff members can control the is_staff field
            self.fields.pop("is_staff", None)

    def save(self, *args, **kwargs):
        """
        Save the form, and set the password, if it has been set
        """
        password = self.cleaned_data.pop("password", None)
        if password is not None:
            self.instance.set_password(password)

        return super().save(*args, **kwargs)
