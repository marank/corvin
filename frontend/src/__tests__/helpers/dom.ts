import { settle } from './render'

/*
 * User-level queries and actions on the whole document (dialogs, overlays and toasts are
 * teleported to <body>). Elements are found the way a user finds them: by their label or
 * accessible name, not by component internals.
 */

const norm = (text: string | null | undefined) => (text ?? '').replace(/\s+/g, ' ').trim()

function accessibleName(el: Element): string {
  return norm(el.getAttribute('aria-label') ?? el.textContent)
}

function describe(root: ParentNode) {
  return root instanceof Element ? root.outerHTML.slice(0, 2000) : 'document'
}

export function within(root: ParentNode = document.body) {
  const scope = {
    root,
    text: () => norm(root.textContent),

    /** Buttons and links named `name`, in document order. */
    buttons(name: string | RegExp): HTMLElement[] {
      return [...root.querySelectorAll<HTMLElement>('button, a, [role="button"]')].filter((el) =>
        typeof name === 'string' ? accessibleName(el) === name : name.test(accessibleName(el)),
      )
    },
    button(name: string | RegExp): HTMLElement {
      const found = scope.buttons(name)
      if (!found.length) throw new Error(`no button "${String(name)}" in ${describe(root)}`)
      return found[0]!
    },
    hasButton: (name: string | RegExp) => scope.buttons(name).length > 0,

    /** The AppFormField group labelled `label` (the trailing " *" of required fields ignored). */
    field(label: string): HTMLElement {
      const groups = [...root.querySelectorAll<HTMLElement>('[role="group"][aria-labelledby]')]
      const group = groups.find((g) => {
        const labelEl = document.getElementById(g.getAttribute('aria-labelledby') ?? '')
        return norm(labelEl?.textContent).replace(/ \*$/, '') === label
      })
      if (!group) throw new Error(`no field "${label}" in ${describe(root)}`)
      return group
    },
    input(label: string): HTMLInputElement {
      const el = scope
        .field(label)
        .querySelector<HTMLInputElement>('input:not([type=checkbox]), textarea')
      if (!el) throw new Error(`field "${label}" has no text input`)
      return el
    },
    /** The error text shown under a field. */
    fieldError(label: string): string {
      // AppFormField puts the error last, after the control (and any hint the caller added).
      const notes = scope.field(label).querySelectorAll(':scope > small')
      return norm(notes[notes.length - 1]?.textContent)
    },
    /** The checkbox of an AppCheckboxField (a <label> around box and text). */
    checkbox(label: string): HTMLInputElement {
      const box = [...root.querySelectorAll('label')]
        .find((l) => norm(l.textContent) === label)
        ?.querySelector<HTMLInputElement>('input[type=checkbox]')
      if (!box) throw new Error(`no checkbox "${label}" in ${describe(root)}`)
      return box
    },
    /** A Select labelled by aria-label instead of a form field. */
    select(name: string): HTMLElement {
      const box = [...root.querySelectorAll('[role="combobox"]')].find(
        (el) => el.getAttribute('aria-label') === name,
      )
      const select = box?.closest<HTMLElement>('.p-select, .p-multiselect')
      if (!select) throw new Error(`no select "${name}" in ${describe(root)}`)
      return select
    },
    /** Rows of the (desktop) table, as their cells' text. */
    rows(): string[][] {
      return [...root.querySelectorAll('tbody tr')]
        .filter((tr) => tr.querySelectorAll('td').length > 1)
        .map((tr) => [...tr.querySelectorAll('td')].map((td) => norm(td.textContent)))
    },
    /** The table row containing `text`. */
    row(text: string): HTMLElement {
      const row = [...root.querySelectorAll<HTMLElement>('tbody tr')].find((tr) =>
        norm(tr.textContent).includes(text),
      )
      if (!row) throw new Error(`no row with "${text}" in ${describe(root)}`)
      return row
    },
  }
  return scope
}

export const screen = within(document.body)

/** The open dialog with this title (the last one if several are stacked). */
export function dialog(title?: string) {
  const dialogs = [
    ...document.querySelectorAll<HTMLElement>('[role="dialog"], [role="alertdialog"]'),
  ]
  const match = title
    ? dialogs.filter((d) => norm(d.querySelector('.p-dialog-title')?.textContent) === title)
    : dialogs
  const found = match[match.length - 1]
  if (!found) throw new Error(`no dialog "${title ?? ''}" open`)
  return within(found)
}

/** The tab panel on show (PrimeVue keeps the others in the DOM, hidden). */
export function activeTab() {
  const panel = [...document.querySelectorAll<HTMLElement>('[role="tabpanel"]')].find(
    (p) => p.style.display !== 'none',
  )
  if (!panel) throw new Error('no tab panel is shown')
  return within(panel)
}

export const isDialogOpen = (title: string) =>
  [...document.querySelectorAll('[role="dialog"], [role="alertdialog"]')].some(
    (d) => norm(d.querySelector('.p-dialog-title')?.textContent) === title,
  )

/** The confirm dialog (useConfirm); answers it with the button named `answer`. */
export async function answerConfirm(answer: string) {
  const confirm = document.querySelector<HTMLElement>('[role="alertdialog"]')
  if (!confirm) throw new Error('no confirmation is open')
  await click(within(confirm).button(answer))
}

export const confirmText = () => norm(document.querySelector('[role="alertdialog"]')?.textContent)

/** Texts of the toasts on screen. */
export function toasts(): string[] {
  return [...document.querySelectorAll('.p-toast-message')].map((el) => norm(el.textContent))
}

/** A full mouse click: PrimeVue reacts to mousedown in places (Select options, overlays). */
export async function click(el: Element) {
  for (const kind of ['mousedown', 'mouseup', 'click'])
    el.dispatchEvent(new MouseEvent(kind, { bubbles: true, cancelable: true }))
  await settle()
}

/** Types into a text field and leaves it (focus, input, blur), as the typed-input fields read on blur. */
export async function type(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  el.dispatchEvent(new FocusEvent('focus'))
  el.dispatchEvent(new FocusEvent('focusin', { bubbles: true }))
  el.value = value
  // PrimeVue's InputNumber edits on keypress and reads the text on blur; it re-renders its
  // old number when given time in between, so input and blur follow each other directly.
  if (!el.closest('.p-inputnumber')) el.dispatchEvent(new Event('input', { bubbles: true }))
  el.dispatchEvent(new FocusEvent('blur'))
  el.dispatchEvent(new FocusEvent('focusout', { bubbles: true }))
  await settle()
}

/** Types without leaving the field, to look at hints shown while typing. */
export async function typeOnly(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  el.dispatchEvent(new FocusEvent('focus'))
  el.value = value
  el.dispatchEvent(new Event('input', { bubbles: true }))
  await settle()
}

export async function pressEnter(el: HTMLElement) {
  el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }))
  await settle()
}

/** Opens the Select/MultiSelect in `container` and clicks the option named `option`. */
export async function choose(container: Element, option: string) {
  const select = container.matches('.p-select, .p-multiselect')
    ? container
    : container.querySelector('.p-select, .p-multiselect')
  if (!select) throw new Error(`no select in ${describe(container)}`)
  await click(select)
  const options = [...document.querySelectorAll<HTMLElement>('[role="option"]')]
  const match = options.find((o) => norm(o.getAttribute('aria-label') ?? o.textContent) === option)
  if (!match)
    throw new Error(
      `no option "${option}", only: ${options.map((o) => norm(o.textContent)).join(' | ')}`,
    )
  await click(match)
}

/** Clears a Select with its clear icon. */
export async function clearSelect(container: Element) {
  const icon = container.querySelector('[data-pc-section="clearicon"]')
  if (!icon) throw new Error('select has no clear icon')
  await click(icon)
}

/** Ticks or unticks the checkbox in `container`. */
export async function toggleCheckbox(container: Element) {
  const box = container.matches('input[type=checkbox]')
    ? (container as HTMLInputElement)
    : container.querySelector<HTMLInputElement>('input[type=checkbox]')
  if (!box) throw new Error(`no checkbox in ${describe(container)}`)
  box.checked = !box.checked
  box.dispatchEvent(new Event('change', { bubbles: true }))
  await settle()
}
