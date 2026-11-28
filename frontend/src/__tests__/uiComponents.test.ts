import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppFormField from '../components/ui/AppFormField.vue'
import { i18n } from '../i18n'

const global = { plugins: [i18n] }

describe('AppIconButton', () => {
  it('is a named button that reports clicks', async () => {
    const wrapper = mount(AppIconButton, {
      props: { icon: 'iconify lucide--play', label: 'Start', title: 'Start timer' },
      global,
    })
    const button = wrapper.get('button')
    expect(button.attributes()).toMatchObject({ type: 'button', 'aria-label': 'Start' })
    expect(button.attributes('title')).toBe('Start timer')
    await button.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('names the common icons itself', () => {
    const wrapper = mount(AppIconButton, { props: { icon: 'iconify lucide--trash-2' }, global })
    expect(wrapper.get('button').attributes('aria-label')).toBe(i18n.global.t('common.delete'))
  })

  it('renders a download link with href', () => {
    const wrapper = mount(AppIconButton, {
      props: {
        icon: 'iconify lucide--download',
        label: 'Export',
        href: '/export.json',
        download: true,
      },
      global,
    })
    const link = wrapper.get('a')
    expect(link.attributes()).toMatchObject({
      href: '/export.json',
      download: '',
      'aria-label': 'Export',
    })
    expect(link.attributes('type')).toBeUndefined()
  })
})

describe('AppFormField', () => {
  it('labels its group and shows the error', () => {
    const wrapper = mount(AppFormField, {
      props: { label: 'Name', required: true, error: 'Required.' },
      slots: { default: '<input />' },
      global,
    })
    const group = wrapper.get('[role="group"]')
    const label = wrapper.get(`#${group.attributes('aria-labelledby')}`)
    expect(label.text()).toBe('Name *')
    expect(wrapper.text()).toContain('Required.')
  })
})
