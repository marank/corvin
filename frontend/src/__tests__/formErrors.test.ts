import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearFormErrors,
  errorText,
  formErrors,
  isFieldShown,
  registerField,
  setFormErrors,
  unregisterField,
} from '../composables/formErrors'

describe('errorText', () => {
  it('joins the messages of a DRF error body', () => {
    expect(errorText(['Required.', 'Too long.'])).toBe('Required., Too long.')
    expect(errorText({ street: ['Required.'], city: { name: 'Unknown.' } })).toBe(
      'Required., Unknown.',
    )
    expect(errorText(0)).toBe('0')
    expect(errorText(false)).toBe('false')
    expect(errorText(null)).toBe('')
    expect(errorText(undefined)).toBe('')
  })
})

describe('form errors', () => {
  beforeEach(clearFormErrors)

  it('keeps one message per field until cleared', () => {
    setFormErrors({ name: ['Required.'], email: 'Invalid.' })
    expect({ ...formErrors }).toEqual({ name: 'Required.', email: 'Invalid.' })
    clearFormErrors()
    expect({ ...formErrors }).toEqual({})
  })

  it('counts the fields that show their errors', () => {
    registerField('name')
    registerField('name')
    unregisterField('name')
    expect(isFieldShown('name')).toBe(true)
    unregisterField('name')
    expect(isFieldShown('name')).toBe(false)
  })
})
