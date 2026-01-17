from django import forms
from django.contrib.auth.hashers import make_password
from core.models import Donor, DonorAddress, FoodDonation
from django.core.validators import MinLengthValidator, RegexValidator

from django import forms
from core.models import Donor, DonorAddress

class DonorRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        validators=[
            MinLengthValidator(8, message="Password must be at least 8 characters long."),
            RegexValidator(
                regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
                message="Password must contain at least one uppercase letter, one lowercase letter, and one number."
            )
        ],
        help_text="Password must be at least 8 characters with uppercase, lowercase letters and numbers."
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    addresses = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your address...',
            'id': 'id_addresses'
        }),
        required=False,
        help_text="Enter addresses (one per line)"
    )
    
    contact = forms.CharField(
        validators=[
            RegexValidator(
                regex='^\+?1?\d{9,15}$',
                message="Enter a valid phone number."
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., +1234567890'
        })
    )

    class Meta:
        model = Donor
        fields = ['name', 'contact', 'location_lat', 'location_long', 'password']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name or organization name'
            }),
            'location_lat': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'location_long': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data

    def save(self, *args, **kwargs):
        donor = super().save(commit=False)
        donor.password = make_password(self.cleaned_data['password'])
        donor.save()

        if self.cleaned_data['addresses']:
            address_list = self.cleaned_data['addresses'].strip().split('\n')
            for address in address_list:
                if address.strip():
                    DonorAddress.objects.create(
                        donor_id=donor,
                        address=address.strip()
                    )
        return donor

    
class DonationEntryForm(forms.ModelForm):
    class Meta:
        model = FoodDonation
        fields = ['food_type', 'quantity', 'unit', 'expiry_time']
        widgets = {
            'expiry_time': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            )
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = ['name', 'contact', 'location_lat', 'location_long']
        # Exclude password as it's sensitive and not meant for update via form