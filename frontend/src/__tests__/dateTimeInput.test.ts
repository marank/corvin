import { describe, expect, it } from 'vitest'
import {
  formatDate,
  formatDateTime,
  formatDuration,
  parseDate,
  parseDateTime,
  parseDuration,
} from '../dateTimeInput'

// Monday, 23 November 2026, 09:15 — what is missing from the typed text comes from here.
const reference = new Date(2026, 10, 23, 9, 15)

describe('parseDateTime', () => {
  it.each([
    ['021126 1800', new Date(2026, 10, 2, 18, 0)],
    ['0211261800', new Date(2026, 10, 2, 18, 0)],
    ['2.11.26 18:00', new Date(2026, 10, 2, 18, 0)],
    ['2.11. 18', new Date(2026, 10, 2, 18, 0)],
    ['2026-11-02 18:00', new Date(2026, 10, 2, 18, 0)],
    ['18:30 Uhr', new Date(2026, 10, 23, 18, 30)],
    ['1800', new Date(2026, 10, 23, 18, 0)],
    ['02.11.2026', new Date(2026, 10, 2, 9, 15)],
  ])('reads %j', (text, expected) => {
    expect(parseDateTime(text, reference)).toEqual(expected)
  })

  it.each(['', '31.02.26 10:00', '25:00', '2.11. 18:75', 'a b c', 'soon'])('refuses %j', (text) => {
    expect(parseDateTime(text, reference)).toBeNull()
  })

  it('reads "18.30" as a time because it is no date', () => {
    expect(parseDateTime('18.30', reference)).toEqual(new Date(2026, 10, 23, 18, 30))
  })
})

describe('parseDate', () => {
  it.each([
    ['2', '2026-11-02'],
    ['0211', '2026-11-02'],
    ['2.11.', '2026-11-02'],
    ['29.02.2028', '2028-02-29'],
  ])('reads %j', (text, expected) => {
    expect(parseDate(text, reference)).toBe(expected)
  })

  it.each(['', '32', '29.02.2027', 'later'])('refuses %j', (text) => {
    expect(parseDate(text, reference)).toBeNull()
  })
})

describe('parseDuration', () => {
  it.each([
    ['3', 180],
    ['3,5', 210],
    ['3.5h', 210],
    ['3:30', 210],
    ['90m', 90],
    ['1h30', 90],
    ['1h 30m', 90],
  ])('reads %j as %i minutes', (text, minutes) => {
    expect(parseDuration(text)).toBe(minutes)
  })

  it.each(['', '3:75', '1h75', 'lots'])('refuses %j', (text) => {
    expect(parseDuration(text)).toBeNull()
  })
})

describe('formatting', () => {
  it('writes dates, durations and date-times the German way', () => {
    expect(formatDate('2026-11-02')).toBe('02.11.2026')
    expect(formatDuration(90)).toBe('01:30')
    expect(formatDuration(-5)).toBe('00:00')
    expect(formatDateTime(new Date(2026, 10, 2, 8, 5))).toBe('02.11.2026 08:05')
  })
})
