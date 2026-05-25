from django import forms
from .models import WithdrawalRequest


class WithdrawalRequestForm(forms.ModelForm):
    """Form for members to request withdrawal."""

    class Meta:
        model = WithdrawalRequest
        fields = ['remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: Add any remarks or reason for withdrawal'
            }),
        }


class WithdrawalApprovalForm(forms.Form):
    """Form for admin to approve withdrawal requests."""

    PAYMENT_METHOD_CHOICES = (
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Payment Method'
    )
    transaction_reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Check number, Bank Ref ID'
        }),
        label='Transaction Reference'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional notes'
        }),
        required=False
    )
