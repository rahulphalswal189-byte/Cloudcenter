"""
context_processors.py
----------------------
Makes storage usage stats and the user's theme preference available
in EVERY template automatically (e.g. for the sidebar storage bar
and the dark/light toggle), without passing them manually from each view.
"""
from .models import UserStorage, UserProfile


def storage_stats(request):
    """Injects `storage` and `theme_preference` into the template context."""
    if request.user.is_authenticated:
        storage, _ = UserStorage.objects.get_or_create(user=request.user)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return {
            'storage': storage,
            'theme_preference': profile.theme_preference,
        }
    return {'storage': None, 'theme_preference': 'light'}
