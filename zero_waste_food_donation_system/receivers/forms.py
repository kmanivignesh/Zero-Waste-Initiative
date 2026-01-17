from django import forms
from core.models import Receiver, ReceiverAddress
from django.core.validators import MinLengthValidator, RegexValidator

class ReceiverRegistrationForm(forms.ModelForm):
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
            'placeholder': 'Enter your address...'
        }), 
        required=False, 
        help_text="Enter multiple addresses, one per line."
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
    
    capacity = forms.IntegerField(
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Storage capacity in kg'
        }),
        help_text="Enter your storage capacity in kilograms (1-10000 kg)."
    )

    class Meta:
        model = Receiver
        fields = ['name', 'contact', 'capacity', 'location_lat', 'location_long', 'password']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
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

    def save(self, commit=True):
        receiver = super().save(commit=False)
        if self.cleaned_data['password']:
            receiver.password = self.cleaned_data['password']  # Handled in model save
        if commit:
            receiver.save()
            if self.cleaned_data['addresses']:
                addresses = self.cleaned_data['addresses'].split('\n')
                for address in addresses:
                    if address.strip():
                        ReceiverAddress.objects.create(receiver_id=receiver, address=address.strip())
        return receiver
    
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Receiver
        fields = ['name', 'contact', 'location_lat', 'location_long']
        # Exclude password as it's sensitive and not meant for update via form   

class CapacityUpdateForm(forms.ModelForm):
    class Meta:
        model = Receiver
        fields = ['capacity']
        widgets = {
            'capacity': forms.NumberInput(attrs={'min': 0})
        }
