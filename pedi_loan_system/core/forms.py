from django import forms
from django.contrib.auth.models import User
from .models import Member, Pedi, Loan

class MemberForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    
    class Meta:
        model = Member
        fields = ['phone', 'address']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['password'].required = False
    
    def save(self, commit=True):
        if self.instance.pk:
            user = self.instance.user
            user.username = self.cleaned_data['username']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            user.save()
            member = super().save(commit=False)
            member.user = user
            if commit:
                member.save()
            return member
        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password']
            )
            member = Member(user=user, role='member', phone=self.cleaned_data['phone'], address=self.cleaned_data['address'])
            if commit:
                member.save()
            return member

class PediForm(forms.ModelForm):
    class Meta:
        model = Pedi
        fields = ['name', 'duration_months', 'monthly_amount', 'start_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['member', 'amount', 'interest_rate', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }