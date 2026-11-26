from django.core.management.base import BaseCommand

from apps.universities.services.media_lifecycle_service import (
    MediaLifecycleService,
)


class Command(BaseCommand):
    help = "Muvaffaqiyatsiz yoki kutilayotgan universitet media cleanup vazifalarini qayta ishlaydi va holatni ko'rsatadi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Bir ishga tushirishda qayta ishlanadigan maksimal vazifalar soni.",
        )
        parser.add_argument(
            "--stats-only",
            action="store_true",
            help="Cleanup bajarmasdan faqat joriy backlog statistikasini chiqaradi.",
        )

    def handle(self, *args, **options):
        if not options["stats_only"]:
            processed = MediaLifecycleService.retry_failed_cleanups(
                limit=options["limit"],
            )
            self.stdout.write(
                f"Processed cleanup tasks: {processed}"
            )

        stats = MediaLifecycleService.get_cleanup_backlog_stats()
        self.stdout.write(
            "Backlog stats: "
            f"pending={stats['pending']}, "
            f"failed={stats['failed']}, "
            f"completed={stats['completed']}, "
            f"cancelled={stats['cancelled']}"
        )
