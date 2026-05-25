from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Member, Pedi, Loan, Notice

class MemberForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    
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
            self.fields['confirm_password'].required = False
        else:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            if not any(char.isdigit() for char in password):
                raise ValidationError('Password must contain at least one digit.')
            if not any(char.isupper() for char in password):
                raise ValidationError('Password must contain at least one uppercase letter.')
            if not any(char.islower() for char in password):
                raise ValidationError('Password must contain at least one lowercase letter.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password or confirm_password:
            if password != confirm_password:
                raise ValidationError('The password and confirm password fields must match.')
        return cleaned_data

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

class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'is_active']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label='Email')

class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(label='New password', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput)

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            if not any(char.isdigit() for char in password):
                raise ValidationError('Password must contain at least one digit.')
            if not any(char.isupper() for char in password):
                raise ValidationError('Password must contain at least one uppercase letter.')
            if not any(char.islower() for char in password):
                raise ValidationError('Password must contain at least one lowercase letter.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('The two password fields didn’t match.')
        return cleaned_data

class PasswordChangeForm(SetPasswordForm):
    old_password = forms.CharField(label='Old password', widget=forms.PasswordInput)

class PediForm(forms.ModelForm):
    class Meta:
        model = Pedi
        fields = [
            'name', 'duration_months', 'monthly_amount', 'start_date', 'is_active',
            'penalty_enabled', 'grace_days',
            'enable_late_fee_per_day', 'late_fee_per_day',
            'enable_fixed_penalty', 'fixed_penalty_amount',
            'enable_percentage_penalty', 'percentage_penalty_rate'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

    LOCKED_MESSAGE = "Financial settings cannot be modified after members or payments are created for this pedi."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.financial_locked = False
        # If editing existing pedi, check for memberships or payments
        pedi = kwargs.get('instance')
        if pedi and pedi.pk:
            from .models import MemberPedi, Payment
            has_members = MemberPedi.objects.filter(pedi=pedi).exists()
            has_payments = Payment.objects.filter(pedi=pedi).exists()
            if has_members or has_payments:
                self.financial_locked = True
                # Disable financial fields in the form (visual only)
                financial_fields = [
                    'monthly_amount', 'duration_months', 'start_date',
                    'penalty_enabled', 'grace_days', 'enable_late_fee_per_day', 'late_fee_per_day',
                    'enable_fixed_penalty', 'fixed_penalty_amount', 'enable_percentage_penalty', 'percentage_penalty_rate'
                ]
                for fname in financial_fields:
                    if fname in self.fields:
                        self.fields[fname].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk and getattr(self, 'financial_locked', False):
            # Ensure locked financial fields are not changed (backend enforcement)
            locked_fields = [
                'monthly_amount', 'duration_months', 'start_date',
                'penalty_enabled', 'grace_days', 'enable_late_fee_per_day', 'late_fee_per_day',
                'enable_fixed_penalty', 'fixed_penalty_amount', 'enable_percentage_penalty', 'percentage_penalty_rate'
            ]
            for field in locked_fields:
                if field in cleaned_data:
                    new_val = cleaned_data.get(field)
                    old_val = getattr(self.instance, field)
                    # For DecimalField and DateField comparisons, normalize
                    if new_val != old_val:
                        raise ValidationError(self.LOCKED_MESSAGE)

        penalty_enabled = cleaned_data.get('penalty_enabled')
        enable_late_fee = cleaned_data.get('enable_late_fee_per_day')
        enable_fixed = cleaned_data.get('enable_fixed_penalty')
        enable_percentage = cleaned_data.get('enable_percentage_penalty')

        if not penalty_enabled:
            cleaned_data['enable_late_fee_per_day'] = False
            cleaned_data['enable_fixed_penalty'] = False
            cleaned_data['enable_percentage_penalty'] = False
        elif enable_late_fee:
            cleaned_data['enable_fixed_penalty'] = False
            cleaned_data['enable_percentage_penalty'] = False
        elif enable_fixed and enable_percentage:
            raise ValidationError('Only one penalty method can be enabled at a time.')

        return cleaned_data

class LoanForm(forms.ModelForm):
    interest_rate = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        label='Interest Rate (%)',
        help_text='Optional. Leave blank to use default loan application settings.',
    )

    class Meta:
        model = Loan
        fields = ['member', 'amount', 'interest_rate']

    LOCKED_MESSAGE = "Loan financial details cannot be changed after payments are recorded."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.financial_locked = False
        loan = kwargs.get('instance')
        if loan and loan.pk:
            from .models import LoanPayment
            if LoanPayment.objects.filter(loan=loan).exists():
                self.financial_locked = True
                for fname in ['amount', 'interest_rate']:
                    if fname in self.fields:
                        self.fields[fname].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk and getattr(self, 'financial_locked', False):
            for field in ['amount', 'interest_rate']:
                if field in cleaned_data:
                    new_val = cleaned_data.get(field)
                    old_val = getattr(self.instance, field)
                    if new_val != old_val:
                        raise ValidationError(self.LOCKED_MESSAGE)
        return cleaned_data




class ReactivateMemberForm(forms.Form):
    """Form for member to reactivate in a pedi."""
    class Meta:
        from .models import Pedi
    
    pedi = forms.ModelChoiceField(
        queryset=Pedi.objects.filter(pedi_status='Active'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select Pedi to Rejoin'
    )
