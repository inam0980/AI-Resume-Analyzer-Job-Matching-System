from django import forms
from .models import Resume, JobDescription


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ('file',)
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.docx,.doc',
            })
        }


class JobDescriptionForm(forms.ModelForm):
    class Meta:
        model = JobDescription
        fields = ('title', 'text', 'file')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title (optional)'}),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Paste the job description here...',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.docx,.doc,.txt',
            }),
        }
