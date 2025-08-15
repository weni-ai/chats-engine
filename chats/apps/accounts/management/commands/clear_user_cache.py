from django.core.management.base import BaseCommand
from django_redis import get_redis_connection
from chats.core.cache_utils import EMAIL_LOOKUP_CACHE_ENABLED


class Command(BaseCommand):
    help = 'Clear all user email cache entries'

    def handle(self, *args, **options):
        if not EMAIL_LOOKUP_CACHE_ENABLED:
            self.stdout.write(self.style.WARNING('Email cache is disabled'))
            return
        
        try:
            r = get_redis_connection()
            pattern = "user:email:*"
            
            deleted_count = 0
            for key in r.scan_iter(match=pattern):
                r.delete(key)
                deleted_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared {deleted_count} cache entries')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing cache: {str(e)}')
            )
