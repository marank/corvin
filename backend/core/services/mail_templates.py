"""E-mail templates: a template and the bases it builds on, its blocks, the mail it renders.

A template without a base is the whole mail, written as HTML; its `{% block name %}` tags
are the blocks others fill. A template with a base is only such blocks, overriding the
base's (`{{ block.super }}` keeps the base's content): Django's own template inheritance,
with the `{% extends %}` added here, one level per base.
"""

import re
from dataclasses import dataclass, field
from html import unescape
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template import Context, Template, TemplateSyntaxError
from django.template.base import TextNode
from django.template.loader_tags import BlockNode, ExtendsNode
from django.utils.translation import gettext as _

from core.models import CompanySettings, MailTemplate

from . import mail_defaults

# Bases a template may build on, counted from itself; deeper chains are a mistake.
MAX_DEPTH = 5


def _chain(template: MailTemplate) -> list[MailTemplate]:
    """The template and its bases, nearest first."""
    chain: list[MailTemplate] = []
    seen: set[Any] = set()
    current: MailTemplate | None = template
    while current is not None:
        if current.pk in seen or len(chain) >= MAX_DEPTH:
            raise ValidationError({"base": _("A template cannot build on itself.")})
        seen.add(current.pk)
        chain.append(current)
        current = current.base
    return chain


def _source(template: MailTemplate, level: int) -> str:
    """Template code for one level: the HTML, extending the next base if there is one."""
    if template.base is None:
        return template.html
    return f"{{% extends mail_base_{level + 1} %}}{template.html}"


def _compile(template: MailTemplate) -> tuple[Template, dict[str, Template]]:
    """The template, and its bases as the context values its `{% extends %}` names."""
    chain = _chain(template)
    bases = {
        f"mail_base_{level}": Template(_source(chain[level], level))
        for level in range(len(chain) - 1, 0, -1)
    }
    return Template(_source(chain[0], 0)), bases


def block_template(base: MailTemplate) -> str:
    """The HTML a new template on `base` starts with: every block of the base, keeping the
    base's content until it is replaced."""
    return "\n\n".join(
        f"{{% block {name} %}}{{{{ block.super }}}}{{% endblock %}}" for name in slot_names(base)
    )


def slot_names(template: MailTemplate) -> list[str]:
    """The blocks a template offers to templates building on it, in order of appearance."""
    names: list[str] = []
    for level, part in reversed(list(enumerate(_chain(template)))):
        nodes = Template(_source(part, level)).nodelist.get_nodes_by_type(BlockNode)
        for node in cast(list[BlockNode], nodes):
            if node.name not in names:
                names.append(node.name)
    return names


def validate_mail_template(template: MailTemplate) -> None:
    """No loops through bases, template code that compiles; on a base only blocks, and only
    ones the base has (anything else would silently not show)."""
    try:
        compiled, _bases = _compile(template)
        Template(template.subject)
    except TemplateSyntaxError as e:
        raise ValidationError(_("Invalid template: %(error)s") % {"error": e}) from e
    if template.base is None:
        return
    extends = cast(ExtendsNode, compiled.nodelist[0])
    outside = [
        node
        for node in extends.nodelist
        if not isinstance(node, BlockNode)
        and not (isinstance(node, TextNode) and not node.s.strip())
    ]
    if outside:
        raise ValidationError(
            {"html": _("With a base, everything goes inside blocks; the rest would not show.")}
        )
    own = [node.name for node in extends.nodelist if isinstance(node, BlockNode)]
    unknown = sorted(set(own) - set(slot_names(template.base)))
    if unknown:
        raise ValidationError(
            {"html": _("The base has no block %(names)s.") % {"names": ", ".join(unknown)}}
        )


@dataclass
class RenderedMail:
    subject: str
    html: str
    text: str
    # Keys of the company images the HTML shows inline (cid:<key>).
    images: list[str] = field(default_factory=list)


def html_to_text(html: str) -> str:
    """The plain-text part of a mail, from its HTML: paragraphs, line breaks, links."""
    text = re.sub(r"(?is)<(head|style|script)\b.*?</\1>", "", html)
    text = re.sub(
        r'(?is)<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: m.group(2) if m.group(1) in m.group(2) else f"{m.group(2)} ({m.group(1)})",
        text,
    )
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)<li\b[^>]*>", "\n- ", text)
    text = re.sub(r"(?i)</(p|h[1-6]|table|ul|ol)>", "\n\n", text)
    text = re.sub(r"(?i)</(div|tr)>", "\n", text)
    text = unescape(re.sub(r"<[^>]+>", "", text))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def render_mail(
    template: MailTemplate, data: dict[str, Any], *, inline_images: bool
) -> RenderedMail:
    """Subject, HTML and text of the mail. Inline: company images as cid:<key>, to be
    attached to the mail; else the image URLs in `data` (previews in the browser)."""
    compiled, bases = _compile(template)
    context = Context({**data, **bases})
    if inline_images:
        context["images"] = {key: f"cid:{key}" for key in data.get("images", {})}
    html = compiled.render(context)
    context.autoescape = False  # a subject is no HTML: "A & B" stays as it is
    subject = " ".join(Template(template.subject).render(context).split())
    used = [key for key in data.get("images", {}) if f"cid:{key}" in html] if inline_images else []
    return RenderedMail(subject=subject, html=html, text=html_to_text(html), images=used)


def _create_defaults(owner: User, layout: MailTemplate | None, kinds: list[str]) -> dict[str, str]:
    """The default templates of the given kinds (and the default layout if needed)."""
    if layout is None:
        layout = MailTemplate.objects.create(
            owner=owner, name=mail_defaults.LAYOUT_NAME, html=mail_defaults.LAYOUT_HTML
        )
    created = {}
    for kind in kinds:
        default = mail_defaults.TEMPLATES[kind]
        template = MailTemplate.objects.create(
            owner=owner,
            name=default["name"],
            subject=default["subject"],
            base=layout,
            html=default["html"],
        )
        created[kind] = str(template.pk)
    return created


def ensure_mail_templates(owner: User) -> dict[str, str]:
    """Every mail kind assigned to one of the owner's templates; the defaults are created
    (with the default layout, if the owner has no template without a base) as needed."""
    with transaction.atomic():
        get_user_model().objects.select_for_update().filter(pk=owner.pk).first()
        company, _created = CompanySettings.objects.get_or_create(user=owner)
        assignments = dict(company.mail_template_assignments or {})
        existing = set(
            str(pk) for pk in MailTemplate.objects.filter(owner=owner).values_list("pk", flat=True)
        )
        missing = [
            kind for kind in MailTemplate.Kind.values if assignments.get(kind) not in existing
        ]
        if missing:
            layout = (
                MailTemplate.objects.filter(owner=owner, base__isnull=True)
                .order_by("created_at")
                .first()
            )
            assignments.update(_create_defaults(owner, layout, missing))
            company.mail_template_assignments = assignments
            company.save(update_fields=["mail_template_assignments"])
    return assignments


def mail_template_for(owner: User, kind: str) -> MailTemplate:
    """The template assigned to a mail kind."""
    return MailTemplate.objects.get(owner=owner, pk=ensure_mail_templates(owner)[kind])


def assigned_kinds(template: MailTemplate) -> list[str]:
    company = CompanySettings.objects.filter(user=template.owner_id).first()
    assignments = getattr(company, "mail_template_assignments", None) or {}
    return [kind for kind, pk in assignments.items() if pk == str(template.pk)]
