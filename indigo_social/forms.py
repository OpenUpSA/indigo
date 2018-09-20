from django import forms

from indigo_social.models import UserProfile


class UserProfileForm(forms.ModelForm):

    first_name = forms.CharField(label='First name')
    last_name = forms.CharField(label='Last name')

    class Meta:
        model = UserProfile
        fields = (
            # personal info (also includes first_name and last_name)
            'profile_photo',
            'bio',
            # work
            'organisations',
            'skills',
            'qualifications',
            'specialisations',
            'areas_of_law',
            # social
            'twitter_profile',
            'linkedin_profile',
        )

    def save(self, commit=True):
        super(UserProfileForm, self).save()
        self.instance.user.first_name = self.cleaned_data['first_name']
        self.instance.user.last_name = self.cleaned_data['last_name']
        self.instance.user.save()
