import { describe, expect, it } from 'vitest'
import { allValues, invoiceStatusValues, taskStatusValues } from '../utils/enums'

describe('allValues', () => {
  it('lists the values in the order written', () => {
    expect(allValues<'b' | 'a'>()({ b: true, a: true })).toEqual(['b', 'a'])
  })

  it('lists every value of the API enums', () => {
    expect(invoiceStatusValues).toEqual(['draft', 'issued', 'sent', 'paid', 'cancelled'])
    expect(taskStatusValues).toEqual(['open', 'in_progress', 'done'])
  })
})
