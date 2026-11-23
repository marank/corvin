// Lenient parsing of typed dates, times and durations (day before month, 24 h clock).
//
// Date and time:  "021126 1800", "0211261800", "2.11.26 18:00", "2.11. 18", "02.11.2026",
//                 "18:00" / "1800" / "18" (time on the current or today's date),
//                 "021126" / "2.11." (date, time kept), "jetzt"/"now", "heute"/"today",
//                 "gestern"/"yesterday", "morgen"/"tomorrow", ISO "2026-11-02 18:00".
// Date alone:     as above, plus "2" (day of this month) and "0211" (day and month).
// Duration:       "3" → 3 h, "3,5" / "3.5" → 3:30, "3:30", "90m", "1h30", "1h 30m".

const KEYWORDS: Record<string, number | 'now'> = {
  jetzt: 'now',
  now: 'now',
  heute: 0,
  today: 0,
  gestern: -1,
  yesterday: -1,
  morgen: 1,
  tomorrow: 1,
}

interface DateParts {
  year: number
  month: number
  day: number
}
interface TimeParts {
  hour: number
  minute: number
}

function fullYear(year: string): number {
  return year.length <= 2 ? 2000 + Number(year) : Number(year)
}

// Capture group `index` of a match; the patterns below only ask for groups they require.
function group(match: RegExpMatchArray, index: number): string {
  return match[index] ?? ''
}

function validDate({ year, month, day }: DateParts): boolean {
  if (month < 1 || month > 12 || day < 1) return false
  return day <= new Date(year, month, 0).getDate()
}

function validTime({ hour, minute }: TimeParts): boolean {
  return hour >= 0 && hour < 24 && minute >= 0 && minute < 60
}

function parseDatePart(token: string, reference: Date): DateParts | null {
  let m = token.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (m) return { year: +group(m, 1), month: +group(m, 2), day: +group(m, 3) }
  // 2.11. / 2.11 / 2.11.26 / 02.11.2026 (also with / or -)
  m = token.match(/^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2}|\d{4})?)?\.?$/)
  if (m) {
    const year = m[3] ? fullYear(m[3]) : reference.getFullYear()
    return { year, month: +group(m, 2), day: +group(m, 1) }
  }
  // ddmmyy / ddmmyyyy
  m = token.match(/^(\d{2})(\d{2})(\d{2}|\d{4})$/)
  if (m) return { year: fullYear(group(m, 3)), month: +group(m, 2), day: +group(m, 1) }
  return null
}

function parseTimePart(token: string): TimeParts | null {
  let m = token.match(/^(\d{1,2})[:.h](\d{2})(?:h|uhr)?$/i)
  if (m) return { hour: +group(m, 1), minute: +group(m, 2) }
  m = token.match(/^(\d{1,2})(?:h|uhr)?$/i)
  if (m) return { hour: +group(m, 1), minute: 0 }
  m = token.match(/^(\d{1,2})(\d{2})$/)
  if (m) return { hour: +group(m, 1), minute: +group(m, 2) }
  return null
}

// A keyword's day, at the time already in the field ("now" is the current moment).
function keywordDateTime(keyword: number | 'now', reference: Date): Date {
  if (keyword === 'now') return new Date()
  const today = new Date()
  const day = new Date(reference)
  day.setFullYear(today.getFullYear(), today.getMonth(), today.getDate() + keyword)
  return day
}

function splitTokens(input: string): string[] {
  const tokens = input.split(/[\sT,]+/).filter(Boolean)
  // Everything in one block of digits: ddmmyyHHMM / ddmmyyyyHHMM.
  const block = tokens.length === 1 ? tokens[0]?.match(/^(\d{6}|\d{8})(\d{4})$/) : null
  return block ? [group(block, 1), group(block, 2)] : tokens
}

interface Parts {
  date: DateParts | null
  time: TimeParts | null
}

// One token: 6/8 digits or a dot are a date ("2.11"), unless that's no valid date ("18.30");
// 1–4 digits or a colon are a time.
function readSingleToken(token: string, reference: Date): Parts | null {
  let date: DateParts | null = null
  if (/^\d{6}$|^\d{8}$|[./-]/.test(token)) {
    date = parseDatePart(token, reference)
    if (date && !validDate(date)) date = null
  }
  const time = date ? null : parseTimePart(token)
  return date || time ? { date, time } : null
}

function readTokens(tokens: string[], reference: Date): Parts | null {
  const [first, second] = tokens
  if (first === undefined || tokens.length > 2) return null
  if (second === undefined) return readSingleToken(first, reference)
  const date = parseDatePart(first, reference)
  const time = parseTimePart(second)
  return date && time ? { date, time } : null
}

/** The typed text as a Date, or null if it can't be read. `reference` supplies what's missing. */
export function parseDateTime(text: string, reference: Date = new Date()): Date | null {
  const input = text
    .trim()
    .toLowerCase()
    .replace(/\s*uhr$/, '')
  if (!input) return null

  const keyword = KEYWORDS[input]
  if (keyword === 'now' || typeof keyword === 'number') return keywordDateTime(keyword, reference)

  const parts = readTokens(splitTokens(input), reference)
  if (!parts) return null
  const { date, time } = parts
  if ((date && !validDate(date)) || (time && !validTime(time))) return null

  const result = new Date(reference)
  result.setSeconds(0, 0)
  if (date) result.setFullYear(date.year, date.month - 1, date.day)
  if (time) result.setHours(time.hour, time.minute)
  return result
}

/**
 * A typed date alone as "YYYY-MM-DD", or null. Without a time to confuse it with, short
 * forms work too: "2" (day of the current month), "0211" (2 November, current year).
 */
export function parseDate(text: string, reference: Date = new Date()): string | null {
  const input = text.trim().toLowerCase()
  if (!input) return null
  let date: DateParts | null
  const keyword = KEYWORDS[input]
  if (keyword !== undefined) {
    const day = new Date()
    day.setDate(day.getDate() + (keyword === 'now' ? 0 : keyword))
    date = { year: day.getFullYear(), month: day.getMonth() + 1, day: day.getDate() }
  } else if (/^\d{1,2}$/.test(input)) {
    date = { year: reference.getFullYear(), month: reference.getMonth() + 1, day: +input }
  } else if (/^\d{4}$/.test(input)) {
    date = { year: reference.getFullYear(), month: +input.slice(2), day: +input.slice(0, 2) }
  } else {
    date = parseDatePart(input, reference)
  }
  if (!date || !validDate(date)) return null
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.year}-${pad(date.month)}-${pad(date.day)}`
}

/** A day as "YYYY-MM-DD" in local time (toISOString() would give the UTC day, before 1 or 2 am yesterday's). */
export function isoDate(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function formatDate(iso: string): string {
  const [year = '', month = '', day = ''] = iso.split('-')
  return `${day}.${month}.${year}`
}

/** Typed duration in minutes, or null. A bare number counts as hours. */
export function parseDuration(text: string): number | null {
  const input = text.trim().toLowerCase().replace(/\s+/g, '')
  if (!input) return null
  let m = input.match(/^(\d+)[:](\d{1,2})h?$/)
  if (m) return hoursAndMinutes(m)
  m = input.match(/^(\d+(?:[.,]\d+)?)h?$/)
  if (m) return Math.round(parseFloat(group(m, 1).replace(',', '.')) * 60)
  m = input.match(/^(\d+)(?:m|min)$/)
  if (m) return +group(m, 1)
  m = input.match(/^(\d+)h(\d{1,2})(?:m|min)?$/)
  if (m) return hoursAndMinutes(m)
  return null
}

// Groups 1 and 2 as hours and minutes; minutes past 59 are no duration.
function hoursAndMinutes(match: RegExpMatchArray): number | null {
  const minutes = +group(match, 2)
  return minutes < 60 ? +group(match, 1) * 60 + minutes : null
}

export function formatDuration(minutes: number): string {
  const m = Math.max(0, Math.round(minutes))
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
}

export function formatDateTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
