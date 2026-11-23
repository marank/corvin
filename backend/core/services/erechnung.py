from datetime import UTC, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from core.models import CompanySettings, Invoice

COUNTRY_IDS = {
    "deutschland": "DE",
    "germany": "DE",
    "österreich": "AT",
    "austria": "AT",
    "schweiz": "CH",
    "switzerland": "CH",
    "france": "FR",
    "frankreich": "FR",
    "netherlands": "NL",
    "niederlande": "NL",
}

UNIT_CODES = {"hours": "HUR", "flat": "C62", "piece": "H87"}


def _country_id(name: str) -> str:
    return COUNTRY_IDS.get(name.strip().lower(), "DE")


def _validate(invoice: Invoice, company: CompanySettings | None) -> CompanySettings:
    missing = []
    if not company or not company.company_name:
        missing.append("company_name")
    if not company or not company.vat_id:
        missing.append("vat_id")
    if (
        invoice.e_invoice_format == Invoice.EInvoiceFormat.XRECHNUNG
        and not invoice.customer.buyer_reference
    ):
        missing.append("customer.buyer_reference (Leitweg-ID)")
    if missing or company is None:
        raise ValidationError(
            {"e_invoice": _("Missing required fields: %(fields)s") % {"fields": ", ".join(missing)}}
        )
    return company


def build_xrechnung_xml(invoice: Invoice) -> bytes:
    """EN 16931 XML (ZUGFeRD/XRechnung CII syntax) for an invoice."""
    from drafthorse.models.accounting import ApplicableTradeTax
    from drafthorse.models.document import Document
    from drafthorse.models.party import TaxRegistration
    from drafthorse.models.payment import PaymentMeans, PaymentTerms
    from drafthorse.models.tradelines import LineItem

    company = _validate(invoice, getattr(invoice.owner, "company_settings", None))

    doc = Document()
    if invoice.e_invoice_format == Invoice.EInvoiceFormat.XRECHNUNG:
        doc.context.guideline_parameter.id = (
            "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
        )
    else:
        doc.context.guideline_parameter.id = (
            "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"
        )

    doc.header.id = invoice.number
    doc.header.type_code = "380"
    issue = datetime.combine(invoice.issue_date, datetime.min.time())
    doc.header.issue_date_time = issue.replace(tzinfo=UTC)

    customer = invoice.customer
    if customer.buyer_reference:
        doc.trade.agreement.buyer_reference = customer.buyer_reference

    seller = doc.trade.agreement.seller
    seller.name = company.company_name
    seller.address.country_id = _country_id(company.country)
    seller.address.line_one = company.street
    seller.address.postcode = company.postal_code
    seller.address.city_name = company.city
    if company.vat_id:
        seller.tax_registrations.add(TaxRegistration(id=("VA", company.vat_id)))

    buyer = doc.trade.agreement.buyer
    buyer.name = customer.name
    buyer.address.country_id = _country_id(customer.country)
    buyer.address.line_one = customer.street
    buyer.address.postcode = customer.postal_code
    buyer.address.city_name = customer.city

    for item in invoice.items.all():
        li = LineItem()
        li.document.line_id = str(item.position)
        li.product.name = item.description
        li.agreement.net.amount = item.unit_price
        li.agreement.net.basis_quantity = (Decimal(1), UNIT_CODES.get(item.unit, "C62"))
        li.delivery.billed_quantity = (item.quantity, UNIT_CODES.get(item.unit, "C62"))
        li.settlement.trade_tax.type_code = "VAT"
        li.settlement.trade_tax.category_code = "S"
        li.settlement.trade_tax.rate_applicable_percent = invoice.vat_rate
        li.settlement.monetary_summation.total_amount = item.total
        doc.trade.items.add(li)

    doc.trade.settlement.currency_code = invoice.currency

    tax = ApplicableTradeTax()
    tax.calculated_amount = invoice.vat_amount
    tax.basis_amount = invoice.subtotal
    tax.type_code = "VAT"
    tax.category_code = "S"
    tax.rate_applicable_percent = invoice.vat_rate
    doc.trade.settlement.trade_tax.add(tax)

    ms = doc.trade.settlement.monetary_summation
    ms.line_total = invoice.subtotal
    ms.tax_basis_total = invoice.subtotal
    ms.tax_total = (invoice.vat_amount, invoice.currency)
    ms.grand_total = invoice.total
    ms.due_amount = invoice.remaining

    bank_account = invoice.bank_account
    if bank_account and bank_account.iban:
        pm = PaymentMeans()
        pm.type_code = "58"  # SEPA credit transfer
        pm.payee_account.iban = bank_account.iban.replace(" ", "")
        doc.trade.settlement.payment_means.add(pm)

    if invoice.due_date:
        pt = PaymentTerms()
        pt.due = invoice.due_date
        doc.trade.settlement.terms.add(pt)

    xml: bytes = doc.serialize()
    return xml
