from typing import Any

from django.core.management.base import BaseCommand

from core.services.contracts import process_due


class Command(BaseCommand):
    help = "Generate invoices for due support contracts."

    def handle(self, *args: Any, **options: Any) -> None:
        invoices = process_due()
        for inv in invoices:
            self.stdout.write(f"Created invoice {inv.number} for {inv.customer.name}")
        self.stdout.write(f"{len(invoices)} invoice(s) generated.")
