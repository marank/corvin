// The variables and snippets the template editors offer (document and e-mail templates).
import type { CompanyImage, TextBlock } from '../api'

export interface VariableGroup {
  label: string
  entries: { label: string; code: string }[]
}

interface TemplateVariableOptions {
  textBlocks: TextBlock[]
  images: CompanyImage[]
  // Document templates: page size, margins and page numbers.
  page?: boolean
  // E-mail templates: the salutation and slots.
  mail?: boolean
}

function escapeAttribute(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/{/g, '&#123;')
}

export function templateVariableGroups(
  t: (key: string) => string,
  { textBlocks, images, page = false, mail = false }: TemplateVariableOptions,
): VariableGroup[] {
  const groups: (VariableGroup | false)[] = [
    mail && {
      label: t('designer.variableGroups.mail'),
      entries: [
        // Salutations: names joins the recipients' names as greeted ("Erika und Max").
        { label: 'Guten Tag …,', code: 'Guten Tag{% if names %} {{ names }}{% endif %},' },
        { label: 'Hallo …,', code: 'Hallo {{ names }},' },
        {
          label: 'Hallo Max, Hallo Erika,',
          code: '{% for r in recipients %}Hallo {{ r.name }}{% if not forloop.last %}, {% endif %}{% endfor %},',
        },
        { label: 'Hallo zusammen,', code: 'Hallo zusammen,' },
        { label: 'names', code: '{{ names }}' },
        { label: 'block', code: '{% block name %}{% endblock %}' },
        { label: 'app_url', code: '{{ app_url }}' },
      ],
    },
    {
      label: t('designer.variableGroups.invoice'),
      entries: [
        'number',
        'issue_date',
        'due_date',
        'status',
        'subtotal',
        'vat_rate',
        'vat_amount',
        'total',
        'currency',
        'notes',
        'amount_paid',
        'remaining',
      ].map((field) => ({ label: field, code: `{{ invoice.${field} }}` })),
    },
    page && {
      label: t('designer.variableGroups.page'),
      entries: [
        'document_type',
        'size',
        'width',
        'height',
        'margin_top',
        'margin_right',
        'margin_bottom',
        'margin_left',
        'header_height',
        'footer_height',
        'font_size',
        'primary_font',
        'secondary_font',
        'primary_color',
        'secondary_color',
        'tertiary_color',
        'background_color',
        'text_color',
      ].map((field) => ({ label: field, code: `{{ page.${field} }}` })),
    },
    page && {
      label: t('designer.variableGroups.pages'),
      entries: [
        { label: 'page_count', code: '{{ page_count }}' },
        {
          label: 'page x of y',
          code: '{% if page_count > 1 %}Seite <span class="page-number"></span> von {{ page_count }}{% endif %}',
        },
      ],
    },
    {
      label: t('designer.variableGroups.customer'),
      entries: [
        'number',
        'name',
        'email',
        'phone',
        'website',
        'vat_id',
        'buyer_reference',
        'street',
        'postal_code',
        'city',
        'country',
      ].map((field) => ({ label: field, code: `{{ customer.${field} }}` })),
    },
    {
      label: t('designer.variableGroups.company'),
      entries: [
        'company_name',
        'street',
        'postal_code',
        'city',
        'country',
        'email',
        'phone',
        'website',
        'tax_id',
        'vat_id',
        'iban',
        'bic',
        'currency',
      ]
        .map((field) => ({ label: field, code: `{{ company.${field} }}` }))
        // The public address: the first entry in APP_URLS.
        .concat({ label: 'app_url', code: '{{ app_url }}' }),
    },
    {
      label: t('designer.variableGroups.bankAccount'),
      entries: ['name', 'bank_name', 'account_holder', 'iban', 'bic'].map((field) => ({
        label: field,
        code: `{{ invoice.bank_account.${field} }}`,
      })),
    },
    {
      label: t('designer.variableGroups.invoiceContacts'),
      entries: [
        {
          label: t('designer.contactLoop'),
          code: '{% for contact in invoice_contacts %}\n{{ contact.name }}{% if not forloop.last %}, {% endif %}\n{% endfor %}',
        },
        { label: 'name', code: '{{ contact.name }}' },
        { label: 'role', code: '{{ contact.role }}' },
        { label: 'email', code: '{{ contact.email }}' },
        { label: 'phone', code: '{{ contact.phone }}' },
      ],
    },
    {
      label: t('designer.variableGroups.companyContacts'),
      entries: [
        {
          label: t('designer.contactLoop'),
          code: '{% for contact in company_contacts %}\n{{ contact.name }} {{ contact.role }} {{ contact.email }} {{ contact.phone }}\n{% endfor %}',
        },
        { label: 'name', code: '{{ contact.name }}' },
        { label: 'role', code: '{{ contact.role }}' },
        { label: 'email', code: '{{ contact.email }}' },
        { label: 'phone', code: '{{ contact.phone }}' },
      ],
    },
    {
      label: t('designer.variableGroups.relations'),
      entries: [
        { label: 'project.number', code: '{{ project.number }}' },
        { label: 'project.name', code: '{{ project.name }}' },
        { label: 'contract.number', code: '{{ contract.number }}' },
        { label: 'contract.name', code: '{{ contract.name }}' },
      ],
    },
    {
      label: t('designer.variableGroups.formatting'),
      entries: [
        { label: 'date', code: '{% display_date invoice.issue_date %}' },
        { label: 'time', code: '{% display_time now %}' },
        { label: 'number', code: '{% display_number invoice.subtotal %}' },
        { label: 'money', code: '{% display_money invoice.total invoice.currency %}' },
      ],
    },
    {
      label: t('designer.variableGroups.lines'),
      entries: [
        {
          label: 'line loop',
          code: '{% for item in items %}\n{{ item.position }} {{ item.description }} {{ item.quantity }} {{ item.unit }} {% display_money item.total invoice.currency %}\n{% endfor %}',
        },
        { label: 'description', code: '{{ item.description }}' },
        { label: 'quantity', code: '{% display_number item.quantity %}' },
        { label: 'unit price', code: '{% display_money item.unit_price invoice.currency %}' },
        { label: 'total', code: '{% display_money item.total invoice.currency %}' },
      ],
    },
    {
      label: t('designer.variableGroups.textBlocks'),
      entries: textBlocks.map((block) => ({
        label: `${block.name} (${block.key})`,
        code: `{{ text_blocks.${block.key} }}`,
      })),
    },
    {
      label: t('designer.variableGroups.images'),
      entries: images.map((image) => ({
        label: image.name,
        code: `<img src="{{ images.${image.key} }}" alt="${escapeAttribute(image.name)}">`,
      })),
    },
  ]
  return groups.filter((group): group is VariableGroup => !!group)
}
