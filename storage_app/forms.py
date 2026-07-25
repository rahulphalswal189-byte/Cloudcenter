"""
forms.py
--------
All Django forms used across the app. Forms are the correct place to
put server-side validation - never trust client-side checks alone.

Includes:
    RegisterForm    - sign-up form with password confirmation
    FileUploadForm  - validates file extension + max upload size
    FolderForm      - create a new folder
    RenameFileForm  - rename an existing file
    ProfileForm     - update avatar / bio / theme
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings

from .models import Folder, UserProfile


class RegisterForm(UserCreationForm):
    """
    Extends Django's built-in UserCreationForm (which already handles
    secure password hashing + confirmation matching) to also collect
    an email address.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(
        attrs={'class': 'form-control', 'placeholder': 'you@example.com'}
    ))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Choose a username'}
        )
        self.fields['password1'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Create a password'}
        )
        self.fields['password2'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Confirm password'}
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class FileUploadForm(forms.Form):
    """
    A lightweight form (not ModelForm) used purely for validating an
    uploaded file's extension and size before we create the File model
    instance ourselves in the view. Supports multiple files via the
    view iterating over request.FILES.getlist('files').
    """
    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={ 'class': 'form-control d-none', 'id': 'fileInput'}),
        required=True,
    )
    folder = forms.ModelChoiceField(queryset=Folder.objects.none(), required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['folder'].queryset = Folder.objects.filter(owner=user)

    @staticmethod
    def validate_single_file(uploaded_file):
        """
        Validates one uploaded file's extension and size.
        Raises forms.ValidationError if invalid; used by the view for
        each file in a multi-file upload.
        """
        # --- Extension whitelist check ---
        ext = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
        if ext not in settings.ALLOWED_FILE_EXTENSIONS:
            raise forms.ValidationError(
                f"'.{ext}' files are not allowed."
            )
        # --- Max size check ---
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"'{uploaded_file.name}' exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit."
            )
        return True


class FolderForm(forms.ModelForm):
    """Create a new folder (feature: Folder Creation)."""
    class Meta:
        model = Folder
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Folder name'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['parent'].queryset = Folder.objects.filter(owner=user)
        self.fields['parent'].required = False


class RenameFileForm(forms.Form):
    """Rename an existing file (feature: Rename Files)."""
    new_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New file name'})
    )


class ProfileForm(forms.ModelForm):
    """Update profile info (feature: User Profile / Settings)."""
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us about yourself'}),
        }
