"""Management command: delete old activity log records."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Delete activity log records older than N days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Delete records older than this many days (default: 90).",
        )
        parser.add_argument(
            "--type",
            dest="event_type",
            default="all",
            choices=["all", "crud", "login", "request", "cors", "system"],
            help="Which event type to purge (default: all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many records would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        from datetime import timedelta

        from django.utils import timezone

        from activitylog.models import (
            CorsEvent,
            CRUDEvent,
            LoginEvent,
            RequestEvent,
            SystemEvent,
        )

        days = options["days"]
        event_type = options["event_type"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        model_map = {
            "crud": CRUDEvent,
            "login": LoginEvent,
            "request": RequestEvent,
            "cors": CorsEvent,
            "system": SystemEvent,
        }

        targets = list(model_map.values()) if event_type == "all" else [model_map[event_type]]

        total = 0
        for model in targets:
            qs = model.objects.filter(datetime__lt=cutoff)
            count = qs.count()
            if not dry_run:
                deleted, _ = qs.delete()
                total += deleted
                self.stdout.write(
                    self.style.SUCCESS(f"{model.__name__}: deleted {deleted} records")
                )
            else:
                total += count
                self.stdout.write(f"{model.__name__}: would delete {count} records")

        label = "Would delete" if dry_run else "Deleted"
        self.stdout.write(
            self.style.SUCCESS(f"{label} {total} total records older than {days} days.")
        )
