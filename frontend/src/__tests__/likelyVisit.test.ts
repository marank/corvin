import { describe, expect, it } from 'vitest'
import { likelyVisit } from '../visits'
import { visit } from './helpers/fixtures'

describe('likelyVisit', () => {
  const morning = visit({ id: 'am', arrival: '08:00:00', departure: '12:00:00' })
  const afternoon = visit({ id: 'pm', arrival: '13:00:00', departure: null })

  it('takes the only visit of the day, whatever the time', () => {
    expect(likelyVisit([morning], '17:00')?.id).toBe('am')
  })

  it('takes the visit whose span holds the time; no departure is open-ended', () => {
    expect(likelyVisit([morning, afternoon], '09:30')?.id).toBe('am')
    expect(likelyVisit([morning, afternoon], '18:00')?.id).toBe('pm')
    expect(likelyVisit([morning, afternoon], '12:30')).toBeUndefined()
  })
})
