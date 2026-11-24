<script setup lang="ts">
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Column from 'primevue/column'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppCheckboxField from '../../components/ui/AppCheckboxField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import {
  bankAccountsApi,
  companyContactsApi,
  companyImagesApi,
  settingsApi,
  type BankAccount,
  type CompanyContact,
  type CompanyImage,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import { useFormattingStore } from '../../stores/formatting'
import { useSettingsStore } from '../../stores/settings'
import { currencies } from '../../currencies'
import HourlyRateList from '../../components/HourlyRateList.vue'
import { tableStateKeys } from '../../tableStateKeys'
import {
  currencyDisplayValues as currencyDisplays,
  currencyPositionValues as currencyPositions,
  numberedEntityValues as entities,
  numberScopeValues,
  openStoppedTimeEntryValues,
  timeRoundingDirectionValues,
} from '../../utils/enums'
import type { components } from '../../api/schema'

interface NumberScheme {
  format: string
  scope: string[]
  start: number
}

const { t } = useI18n()
// ?tab=bankAccounts etc. opens a tab directly (e.g. from the invoice IBAN hint).
const tab = ref(
  typeof useRoute().query.tab === 'string' ? (useRoute().query.tab as string) : 'company',
)
// Bank accounts, contacts and images save in their own dialogs; Save is for the form tabs.
const formTabs = ['company', 'numbering', 'timeTracking']
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const formatting = useFormattingStore()
const settingsStore = useSettingsStore()
const form = ref<Record<string, unknown>>({})
const saving = ref(false)
type Entity = components['schemas']['EntityEnum']
// One value per numbered entity.
const perEntity = <V,>(value: (entity: Entity) => V) =>
  Object.fromEntries(entities.map((entity) => [entity, value(entity)])) as Record<Entity, V>
const scopes = numberScopeValues.map((value) => ({
  value,
  label: t(`settings.scopes.${value}`),
}))
const roundingDirections = timeRoundingDirectionValues.map((value) => ({
  label: t(`settings.roundingDirections.${value}`),
  value,
}))
const openStoppedTimeEntryOptions = openStoppedTimeEntryValues.map((value) => ({
  label: t(`common.${value}`),
  value,
}))
const defaultSchemes: Record<Entity, NumberScheme> = {
  customer: { format: 'K-{counter:4}', scope: [], start: 1000 },
  project: { format: 'P-{counter:4}', scope: ['customer'], start: 1 },
  invoice: { format: 'RE-{year:4}-{counter:4}', scope: ['year'], start: 1 },
  contract: { format: 'V-{counter:4}', scope: [], start: 1 },
  visit: { format: 'B-{year:4}-{counter:4}', scope: ['year'], start: 1 },
  task: { format: 'T-{counter:4}', scope: ['project'], start: 1 },
}
const schemes = ref(perEntity((entity) => ({ ...defaultSchemes[entity] })))
const { markSaved } = useUnsavedChanges(computed(() => [form.value, schemes.value]))
const previews = ref<Record<string, string>>({})
const bankAccounts = ref<BankAccount[]>([])
const bankAccountModal = ref<InstanceType<typeof AppModal>>()
const editingBankAccount = ref<BankAccount | null>(null)
const bankAccountForm = ref<Partial<BankAccount>>({ is_active: true })
const contacts = ref<CompanyContact[]>([])
const contactModal = ref<InstanceType<typeof AppModal>>()
const editingContact = ref<CompanyContact | null>(null)
const contactForm = ref<Partial<CompanyContact>>({})
const images = ref<CompanyImage[]>([])
const imageModal = ref<InstanceType<typeof AppModal>>()
const additionalImage = ref({ key: '', name: '', file: null as File | null })
const fixedImageKinds = ['logo_light', 'logo_dark', 'icon_light', 'icon_dark']
let previewTimer: ReturnType<typeof setTimeout> | undefined

function normalizeSchemes(value: unknown): Record<Entity, NumberScheme> {
  const stored = (value ?? {}) as Record<
    string,
    // Older settings stored the scope as one name (see legacyScopes).
    Omit<Partial<NumberScheme>, 'scope'> & { scope?: string[] | string }
  >
  const legacyScopes: Record<string, string[]> = {
    global: [],
    year: ['year'],
    customer: ['customer'],
    project: ['project'],
    customer_year: ['customer', 'year'],
    project_year: ['project', 'year'],
  }
  return perEntity((entity) => {
    const configured = stored[entity] ?? {}
    const scope = Array.isArray(configured.scope)
      ? configured.scope
      : (legacyScopes[configured.scope ?? 'global'] ?? [])
    return { ...defaultSchemes[entity], ...configured, scope }
  })
}

onMounted(async () => {
  const [settings, bankAccountPage, contactPage, imagePage] = await Promise.all([
    settingsApi.get(),
    bankAccountsApi.list(),
    companyContactsApi.list(),
    companyImagesApi.list(),
  ])
  form.value = settings
  settingsStore.apply(settings)
  bankAccounts.value = bankAccountPage.results
  contacts.value = contactPage.results
  images.value = imagePage.results
  // The schemes watcher loads their previews.
  schemes.value = normalizeSchemes(form.value.numbering_schemes)
  markSaved()
})
onBeforeUnmount(() => clearTimeout(previewTimer))

watch(
  schemes,
  () => {
    clearTimeout(previewTimer)
    previewTimer = setTimeout(() => void loadPreviews(), 250)
  },
  { deep: true },
)

async function loadPreviews() {
  await Promise.all(
    entities.map(async (entity) => {
      const scheme = schemes.value[entity]
      if (!scheme.format) return
      try {
        previews.value[entity] = (await settingsApi.previewNumber({ entity, ...scheme })).preview
      } catch {
        previews.value[entity] = '—'
      }
    }),
  )
}

function openBankAccount(account?: BankAccount) {
  editingBankAccount.value = account ?? null
  bankAccountForm.value = account ? { ...account } : { is_active: true }
  bankAccountModal.value?.open()
}

async function saveBankAccount() {
  try {
    if (editingBankAccount.value) {
      await bankAccountsApi.update(editingBankAccount.value.id, bankAccountForm.value)
    } else {
      await bankAccountsApi.create(bankAccountForm.value)
    }
    bankAccounts.value = (await bankAccountsApi.list()).results
    bankAccountModal.value?.close()
    notify.ok(t('common.saved'))
    bankAccountForm.value = { is_active: true }
  } catch (e) {
    notify.error(e)
  }
}

async function setDefaultBankAccount(account: BankAccount) {
  try {
    form.value = await settingsApi.update({ default_bank_account: account.id })
    markSaved()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  }
}

function removeBankAccount(account: BankAccount) {
  confirmDelete(async () => {
    await bankAccountsApi.remove(account.id)
    bankAccounts.value = bankAccounts.value.filter((item) => item.id !== account.id)
    if (form.value.default_bank_account === account.id) form.value.default_bank_account = null
  })
}

function openContact(contact?: CompanyContact) {
  editingContact.value = contact ?? null
  contactForm.value = contact ? { ...contact } : {}
  contactModal.value?.open()
}

async function saveContact() {
  try {
    if (editingContact.value) {
      await companyContactsApi.update(editingContact.value.id, contactForm.value)
    } else {
      await companyContactsApi.create(contactForm.value)
    }
    contacts.value = (await companyContactsApi.list()).results
    contactModal.value?.close()
    notify.ok(t('common.saved'))
    contactForm.value = {}
  } catch (e) {
    notify.error(e)
  }
}

function removeContact(contact: CompanyContact) {
  confirmDelete(async () => {
    await companyContactsApi.remove(contact.id)
    contacts.value = contacts.value.filter((item) => item.id !== contact.id)
  })
}

function imageFor(kind: string) {
  return images.value.find((image) => image.kind === kind)
}

async function uploadFixedImage(kind: string, event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const existing = imageFor(kind)
  try {
    await companyImagesApi.upload(
      {
        kind,
        key: kind,
        name: t(`settings.imageKinds.${kind}`),
        file,
      },
      existing?.id,
    )
    images.value = (await companyImagesApi.list()).results
  } catch (e) {
    notify.error(e)
  }
}

function openAdditionalImage() {
  additionalImage.value = { key: '', name: '', file: null }
  imageModal.value?.open()
}

function selectAdditionalFile(event: Event) {
  additionalImage.value.file = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function uploadAdditionalImage() {
  const data = additionalImage.value
  if (!data.file || !data.key || !data.name) return
  try {
    await companyImagesApi.upload({
      kind: 'additional',
      key: data.key,
      name: data.name,
      file: data.file,
    })
    images.value = (await companyImagesApi.list()).results
    imageModal.value?.close()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  }
}

function removeImage(image: CompanyImage) {
  confirmDelete(async () => {
    await companyImagesApi.remove(image.id)
    images.value = images.value.filter((item) => item.id !== image.id)
  })
}

async function save() {
  saving.value = true
  try {
    form.value.numbering_schemes = schemes.value
    form.value = await settingsApi.update(form.value)
    formatting.apply(form.value)
    settingsStore.apply(form.value)
    schemes.value = normalizeSchemes(form.value.numbering_schemes)
    markSaved()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('settings.title')">
      <template #actions>
        <Button
          v-if="formTabs.includes(tab)"
          :label="t('common.save')"
          :loading="saving"
          @click="save"
        />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="company">{{ t('settings.company') }}</Tab>
        <Tab value="bankAccounts">{{ t('settings.bankAccounts') }}</Tab>
        <Tab value="contacts">{{ t('settings.companyContacts') }}</Tab>
        <Tab value="images">{{ t('settings.images') }}</Tab>
        <Tab value="numbering">{{ t('settings.numbering') }}</Tab>
        <Tab value="timeTracking">{{ t('settings.timeTracking') }}</Tab>
        <Tab value="rates">{{ t('rates.title') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="company">
          <div class="flex flex-col gap-6 max-w-3xl pt-4">
            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('settings.groups.company') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="company_name" :label="t('settings.companyName')"
                  ><InputText v-model="form.company_name as string" class="w-full"
                /></AppFormField>
                <AppFormField field="email" :label="t('common.email')"
                  ><InputText v-model="form.email as string" class="w-full"
                /></AppFormField>
                <AppFormField field="phone" :label="t('common.phone')"
                  ><InputText v-model="form.phone as string" class="w-full"
                /></AppFormField>
                <AppFormField field="website" :label="t('settings.website')"
                  ><InputText v-model="form.website as string" class="w-full"
                /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('settings.groups.address') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="street" :label="t('customers.street')" class="md:col-span-2"
                  ><InputText v-model="form.street as string" class="w-full"
                /></AppFormField>
                <AppFormField field="postal_code" :label="t('customers.postalCode')"
                  ><InputText v-model="form.postal_code as string" class="w-full"
                /></AppFormField>
                <AppFormField field="city" :label="t('settings.city')"
                  ><InputText v-model="form.city as string" class="w-full"
                /></AppFormField>
                <AppFormField field="country" :label="t('settings.country')"
                  ><InputText v-model="form.country as string" class="w-full"
                /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('settings.groups.tax') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="tax_id" :label="t('settings.taxId')"
                  ><InputText v-model="form.tax_id as string" class="w-full"
                /></AppFormField>
                <AppFormField field="vat_id" :label="t('settings.vatId')"
                  ><InputText v-model="form.vat_id as string" class="w-full"
                /></AppFormField>
                <AppCheckboxField
                  v-model="form.vat_enabled as boolean"
                  :label="t('settings.vatEnabled')"
                />
                <AppFormField field="default_vat_rate" :label="t('settings.defaultVat')"
                  ><InputNumber
                    v-model="form.default_vat_rate as number"
                    :min="0"
                    :min-fraction-digits="2"
                    class="w-full"
                    :disabled="form.vat_enabled === false"
                /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('settings.groups.formatting') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="date_format" :label="t('settings.dateFormat')"
                  ><InputText v-model="form.date_format as string" class="w-full font-mono"
                /></AppFormField>
                <AppFormField field="time_format" :label="t('settings.timeFormat')"
                  ><InputText v-model="form.time_format as string" class="w-full font-mono"
                /></AppFormField>
                <AppFormField field="decimal_separator" :label="t('settings.decimalSeparator')"
                  ><InputText
                    v-model="form.decimal_separator as string"
                    maxlength="1"
                    class="w-full"
                /></AppFormField>
                <AppFormField field="thousands_separator" :label="t('settings.thousandsSeparator')"
                  ><InputText
                    v-model="form.thousands_separator as string"
                    maxlength="1"
                    class="w-full"
                /></AppFormField>
                <AppFormField :label="t('settings.currency')">
                  <Select
                    v-model="form.currency"
                    :options="currencies"
                    option-label="label"
                    option-value="code"
                    filter
                    class="w-full"
                  />
                </AppFormField>
                <AppFormField :label="t('settings.currencyDisplay')">
                  <AppEnumSelect
                    v-model="form.currency_display as string"
                    :options="currencyDisplays"
                    label-prefix="settings.currencyDisplays"
                    class="w-full"
                  />
                </AppFormField>
                <AppFormField :label="t('settings.currencyPosition')">
                  <AppEnumSelect
                    v-model="form.currency_position as string"
                    :options="currencyPositions"
                    label-prefix="settings.currencyPositions"
                    class="w-full"
                  />
                </AppFormField>
                <AppCheckboxField
                  v-model="form.currency_space as boolean"
                  :label="t('settings.currencySpace')"
                />
              </div>
              <p class="text-xs text-surface-500 mt-3">{{ t('settings.formatHelp') }}</p>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('settings.groups.invoicing') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="payment_terms_days" :label="t('settings.paymentTerms')"
                  ><InputNumber v-model="form.payment_terms_days as number" :min="0" class="w-full"
                /></AppFormField>
              </div>
            </fieldset>
          </div>
        </TabPanel>
        <TabPanel value="bankAccounts">
          <div class="pt-4">
            <div class="flex justify-end mb-3">
              <Button
                :label="t('settings.newBankAccount')"
                icon="pi pi-plus"
                size="small"
                @click="openBankAccount()"
              />
            </div>
            <AppDataTable
              :rows="bankAccounts"
              :state-key="tableStateKeys.settingsBankAccounts"
              @row-click="openBankAccount"
            >
              <Column class="app-text" field="name" :header="t('common.name')" sortable />
              <Column
                class="app-text"
                field="bank_name"
                :header="t('settings.bankName')"
                sortable
              />
              <Column
                class="app-text"
                field="account_holder"
                :header="t('settings.accountHolder')"
                sortable
              />
              <Column field="iban" :header="t('settings.iban')" sortable />
              <Column field="bic" :header="t('settings.bic')" sortable />
              <Column :header="t('settings.defaultBankAccount')" :reorderable-column="false">
                <template #body="{ data }">
                  <i v-if="form.default_bank_account === data.id" class="pi pi-check" />
                  <Button
                    v-else-if="data.is_active"
                    icon="pi pi-star"
                    text
                    size="small"
                    @click.stop="setDefaultBankAccount(data)"
                  />
                </template>
              </Column>
              <Column :header="t('common.actions')" :reorderable-column="false">
                <template #body="{ data }"
                  ><AppIconButton
                    icon="pi pi-trash"
                    severity="danger"
                    @click.stop="removeBankAccount(data)"
                /></template>
              </Column>
            </AppDataTable>
          </div>
        </TabPanel>
        <TabPanel value="contacts">
          <div class="pt-4">
            <div class="flex justify-end mb-3">
              <Button
                :label="t('settings.newCompanyContact')"
                icon="pi pi-plus"
                size="small"
                @click="openContact()"
              />
            </div>
            <AppDataTable
              :rows="contacts"
              :state-key="tableStateKeys.settingsCompanyContacts"
              @row-click="openContact"
            >
              <Column field="first_name" :header="t('customers.firstName')" sortable />
              <Column field="last_name" :header="t('customers.lastName')" sortable />
              <Column class="app-text" field="role" :header="t('customers.role')" sortable />
              <Column class="app-text" field="email" :header="t('common.email')" sortable />
              <Column field="phone" :header="t('common.phone')" sortable />
              <Column :header="t('common.actions')" :reorderable-column="false">
                <template #body="{ data }"
                  ><AppIconButton
                    icon="pi pi-trash"
                    severity="danger"
                    @click.stop="removeContact(data)"
                /></template>
              </Column>
            </AppDataTable>
          </div>
        </TabPanel>
        <TabPanel value="images">
          <div class="pt-4 flex flex-col gap-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="kind in fixedImageKinds"
                :key="kind"
                class="border-t border-surface-200 dark:border-surface-700 pt-4"
              >
                <h3 class="font-medium mb-3">{{ t(`settings.imageKinds.${kind}`) }}</h3>
                <div
                  class="h-36 border border-surface-200 dark:border-surface-700 flex items-center justify-center bg-surface-50 dark:bg-surface-900 mb-3"
                >
                  <img
                    v-if="imageFor(kind)"
                    :src="imageFor(kind)!.url"
                    :alt="t(`settings.imageKinds.${kind}`)"
                    class="max-h-full max-w-full object-contain"
                  />
                  <span v-else class="text-sm text-surface-500">{{ t('common.empty') }}</span>
                </div>
                <div class="flex gap-2">
                  <label class="p-button p-component p-button-sm cursor-pointer">
                    <i class="pi pi-upload mr-2" />{{ t('settings.uploadImage') }}
                    <input
                      type="file"
                      accept="image/*"
                      class="hidden"
                      @change="uploadFixedImage(kind, $event)"
                    />
                  </label>
                  <AppIconButton
                    v-if="imageFor(kind)"
                    icon="pi pi-trash"
                    severity="danger"
                    @click="removeImage(imageFor(kind)!)"
                  />
                </div>
              </div>
            </div>

            <div class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="font-medium">{{ t('settings.additionalImages') }}</h3>
                <Button
                  :label="t('settings.addImage')"
                  icon="pi pi-plus"
                  size="small"
                  @click="openAdditionalImage"
                />
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div
                  v-for="image in images.filter((item) => item.kind === 'additional')"
                  :key="image.id"
                  class="border border-surface-200 dark:border-surface-700 p-3"
                >
                  <img :src="image.url" :alt="image.name" class="w-full h-24 object-contain mb-2" />
                  <div class="font-medium text-sm truncate">{{ image.name }}</div>
                  <code class="text-xs text-surface-500">{{ image.key }}</code>
                  <AppIconButton
                    icon="pi pi-trash"
                    severity="danger"
                    class="float-right"
                    @click="removeImage(image)"
                  />
                </div>
              </div>
            </div>
          </div>
        </TabPanel>
        <TabPanel value="numbering">
          <div class="pt-4">
            <p class="text-sm text-surface-500 mb-4">{{ t('settings.numberingHelp') }}</p>
            <div class="border border-surface-200 dark:border-surface-700">
              <div
                class="hidden lg:grid grid-cols-[160px_1fr_180px_140px_220px] gap-3 px-3 py-2 border-b border-surface-200 dark:border-surface-700 text-sm font-medium"
              >
                <span>{{ t('common.name') }}</span>
                <span>{{ t('settings.numberFormat') }}</span>
                <span>{{ t('settings.numberScope') }}</span>
                <span>{{ t('settings.numberStart') }}</span>
                <span>{{ t('settings.numberPreview') }}</span>
              </div>
              <div
                v-for="entity in entities"
                :key="entity"
                class="grid grid-cols-1 lg:grid-cols-[160px_1fr_180px_140px_220px] gap-3 px-3 py-3 border-b last:border-b-0 border-surface-200 dark:border-surface-700 items-end"
              >
                <div class="font-medium lg:self-center">{{ t(`settings.entities.${entity}`) }}</div>
                <AppFormField
                  :label="t('settings.numberFormat')"
                  class="lg:[&>.app-form-field-label]:hidden"
                  ><InputText v-model="schemes[entity].format" class="w-full font-mono"
                /></AppFormField>
                <AppFormField
                  :label="t('settings.numberScope')"
                  class="lg:[&>.app-form-field-label]:hidden"
                >
                  <MultiSelect
                    v-model="schemes[entity].scope"
                    :show-toggle-all="false"
                    :options="scopes"
                    option-label="label"
                    option-value="value"
                    class="w-full"
                    display="chip"
                    :placeholder="t('settings.scopes.global')"
                  />
                </AppFormField>
                <AppFormField
                  :label="t('settings.numberStart')"
                  class="lg:[&>.app-form-field-label]:hidden"
                  ><InputNumber v-model="schemes[entity].start" :min="1" fluid
                /></AppFormField>
                <div
                  class="font-mono text-sm bg-surface-100 dark:bg-surface-800 px-3 py-2 min-h-10 break-all"
                >
                  {{ previews[entity] || '—' }}
                </div>
              </div>
            </div>
          </div>
        </TabPanel>
        <TabPanel value="rates">
          <div class="max-w-3xl pt-4"><HourlyRateList /></div>
        </TabPanel>
        <TabPanel value="timeTracking">
          <div class="flex flex-col gap-6 max-w-3xl pt-4">
            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('settings.groups.timeTracking') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField :label="t('settings.timeRoundingStartDirection')">
                  <Select
                    v-model="form.time_rounding_start_direction"
                    :options="roundingDirections"
                    option-label="label"
                    option-value="value"
                    class="w-full"
                  />
                </AppFormField>
                <AppFormField :label="t('settings.timeRoundingStartMinutes')">
                  <InputNumber
                    v-model="form.time_rounding_start_minutes as number"
                    :min="1"
                    class="w-full"
                  />
                </AppFormField>
                <AppFormField :label="t('settings.timeRoundingEndDirection')">
                  <Select
                    v-model="form.time_rounding_end_direction"
                    :options="roundingDirections"
                    option-label="label"
                    option-value="value"
                    class="w-full"
                  />
                </AppFormField>
                <AppFormField :label="t('settings.timeRoundingEndMinutes')">
                  <InputNumber
                    v-model="form.time_rounding_end_minutes as number"
                    :min="1"
                    class="w-full"
                  />
                </AppFormField>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <AppCheckboxField
                  v-model="form.timer_counts_during_break as boolean"
                  :label="t('settings.timerCountsDuringBreak')"
                />
                <AppCheckboxField
                  v-model="form.always_show_timer_widget as boolean"
                  :label="t('settings.alwaysShowTimerWidget')"
                />
                <AppFormField :label="t('settings.openStoppedTimeEntry')">
                  <Select
                    v-model="form.open_stopped_time_entry"
                    :options="openStoppedTimeEntryOptions"
                    option-label="label"
                    option-value="value"
                    class="w-full"
                  />
                </AppFormField>
              </div>
            </fieldset>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal
      ref="bankAccountModal"
      :form="bankAccountForm"
      :title="editingBankAccount ? t('settings.editBankAccount') : t('settings.newBankAccount')"
      @confirm="saveBankAccount"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="name" :label="t('common.name')" required
          ><InputText v-model="bankAccountForm.name" class="w-full"
        /></AppFormField>
        <AppFormField field="bank_name" :label="t('settings.bankName')"
          ><InputText v-model="bankAccountForm.bank_name" class="w-full"
        /></AppFormField>
        <AppFormField field="account_holder" :label="t('settings.accountHolder')" required
          ><InputText v-model="bankAccountForm.account_holder" class="w-full"
        /></AppFormField>
        <AppFormField field="iban" :label="t('settings.iban')" required
          ><InputText v-model="bankAccountForm.iban" class="w-full"
        /></AppFormField>
        <AppFormField field="bic" :label="t('settings.bic')"
          ><InputText v-model="bankAccountForm.bic" class="w-full"
        /></AppFormField>
        <AppCheckboxField v-model="bankAccountForm.is_active" :label="t('customers.active')" />
      </div>
    </AppModal>

    <AppModal
      ref="contactModal"
      :form="contactForm"
      :title="editingContact ? t('settings.editCompanyContact') : t('settings.newCompanyContact')"
      @confirm="saveContact"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-3">
          <AppFormField field="first_name" :label="t('customers.firstName')" required
            ><InputText v-model="contactForm.first_name" class="w-full"
          /></AppFormField>
          <AppFormField field="last_name" :label="t('customers.lastName')"
            ><InputText v-model="contactForm.last_name" class="w-full"
          /></AppFormField>
        </div>
        <AppFormField field="role" :label="t('customers.role')"
          ><InputText v-model="contactForm.role" class="w-full"
        /></AppFormField>
        <AppFormField field="email" :label="t('common.email')"
          ><InputText v-model="contactForm.email" class="w-full"
        /></AppFormField>
        <AppFormField field="phone" :label="t('common.phone')"
          ><InputText v-model="contactForm.phone" class="w-full"
        /></AppFormField>
      </div>
    </AppModal>

    <AppModal ref="imageModal" :title="t('settings.addImage')" @confirm="uploadAdditionalImage">
      <div class="flex flex-col gap-4">
        <AppFormField field="name" :label="t('common.name')" required
          ><InputText v-model="additionalImage.name" class="w-full"
        /></AppFormField>
        <AppFormField field="key" :label="t('settings.imageKey')" required
          ><InputText v-model="additionalImage.key" class="w-full"
        /></AppFormField>
        <AppFormField :label="t('settings.imageFile')" required
          ><input type="file" accept="image/*" @change="selectAdditionalFile"
        /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
