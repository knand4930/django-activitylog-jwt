"""Management command: verify integrity hashes across all log tables."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify integrity hashes for all activity log records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix", action="store_true",
            help="Recompute and save hashes for records that fail verification.",
        )
        parser.add_argument(
            "--model", dest="model_name", default=None,
            choices=["CRUDEvent", "LoginEvent", "RequestEvent", "CorsEvent", "SystemEvent"],
            help="Limit verification to a single model.",
        )

    def handle(self, *args, **options):
        from activitylog.security.integrity import IntegrityChecker
        from activitylog.models import CRUDEvent, LoginEvent, RequestEvent, CorsEvent, SystemEvent

        checker = IntegrityChecker()
        model_name = options.get("model_name")
        fix = options["fix"]

        model_map = {
            "CRUDEvent": CRUDEvent,
            "LoginEvent": LoginEvent,
            "RequestEvent": RequestEvent,
            "CorsEvent": CorsEvent,
            "SystemEvent": SystemEvent,
        }

        if model_name:
            model = model_map[model_name]
            results = {model_name: checker._check_model(model, fix)}
        else:
            results = checker.check_all(fix=fix)

        any_tampered = False
        for name, info in results.items():
            tampered = info["tampered"]
            if tampered:
                any_tampered = True
                self.stdout.write(
                    self.style.ERROR(
                        f"{name}: {tampered}/{info['total']} records TAMPERED"
                        + (f" ({info['fixed']} fixed)" if fix else "")
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"{name}: {info['total']} records OK")
                )

        if any_tampered and not fix:
            self.stdout.write(
                self.style.WARNING("Run with --fix to recompute integrity hashes.")
            )
