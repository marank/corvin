import type { Visit } from './api'

export const hhmm = (time: string | null) => time?.slice(0, 5) ?? ''

// The visit a time entry starting at `time` most likely belongs to: the only one of the day,
// else the one whose time span holds it (no departure: open until the end of the day).
export function likelyVisit(candidates: Visit[], time: string): Visit | undefined {
  if (candidates.length === 1) return candidates[0]
  return candidates.find(
    (visit) =>
      visit.arrival &&
      hhmm(visit.arrival) <= time &&
      (!visit.departure || time < hhmm(visit.departure)),
  )
}
