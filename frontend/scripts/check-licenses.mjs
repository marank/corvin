// Fail if a production dependency's license can't be combined with this app's
// AGPL-3.0-or-later, or is proprietary / unknown (e.g. PrimeVue 5's
// "SEE LICENSE IN LICENSE.md"). Reads `pnpm licenses list --prod --json`.
//
// Fine: permissive licenses, MPL-2.0, LGPL, GPL-3.0, AGPL-3.0, GPL-2.0-or-later.
// Not fine: GPL-2.0-only, SSPL, EPL-1.0, CDDL, BSD-4-Clause, proprietary/unknown.
// SPDX expressions with OR pass when one of the options is fine.
import { execFileSync } from 'node:child_process'

const INCOMPATIBLE =
  /SSPL|EPL-1\.0|CDDL|BSD-4-Clause|(?<![LA])GPL-?2(\.0)?-only|(?<![LA])GPL-2\.0$|(?<![LA])GPLv2(?!\+)/i
// "Unlicense" is public domain and doesn't match.
const PROPRIETARY = /SEE LICENSE IN|\bUNLICENSED\b|proprietary|commercial|^\s*Unknown\s*$/i
// Packages whose metadata is wrong or ambiguous, after checking them by hand:
// { 'package-name': 'reason' }
const ALLOW = {}

const acceptable = (license) =>
  license
    .replace(/[()]/g, '')
    .split(/\s+OR\s+/i)
    .some((option) => !INCOMPATIBLE.test(option.trim()) && !PROPRIETARY.test(option.trim()))

const byLicense = JSON.parse(
  execFileSync('pnpm', ['licenses', 'list', '--prod', '--json'], { encoding: 'utf8' }),
)
const bad = []
for (const [license, packages] of Object.entries(byLicense)) {
  if (acceptable(license)) continue
  for (const pkg of packages) {
    if (!(pkg.name in ALLOW)) bad.push(`${pkg.name} ${pkg.versions?.join(', ') ?? ''}: ${license}`)
  }
}
for (const line of bad) console.log(`license not compatible with AGPL-3.0-or-later: ${line}`)
if (!bad.length) console.log('licenses ok')
process.exit(bad.length ? 1 : 0)
