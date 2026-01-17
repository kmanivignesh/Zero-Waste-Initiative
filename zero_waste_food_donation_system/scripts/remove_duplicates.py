import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from core.models import Donor
from django.db.models import Count

duplicates = Donor.objects.values('name').annotate(name_count=Count('id')).filter(name_count__gt=1)

for dup in duplicates:
    name = dup['name']
    donors_to_keep = Donor.objects.filter(name=name).order_by('id')[:1]
    donors_to_delete = Donor.objects.filter(name=name).exclude(id=donors_to_keep[0].id)
    count_deleted, _ = donors_to_delete.delete()
    print(f"Kept {donors_to_keep[0].id} for name '{name}', deleted {count_deleted} duplicates.")

check_duplicates = Donor.objects.values('name').annotate(name_count=Count('id')).filter(name_count__gt=1)
print("Remaining duplicates:", list(check_duplicates))
