import { describe, expect, it } from 'vitest'
import { firstLine, markdownRenderer } from '../markdown'

describe('markdownRenderer', () => {
  it('renders Markdown and escapes raw HTML', async () => {
    const render = await markdownRenderer()
    expect(render('**fett** <script>alert(1)</script>')).toBe(
      '<p><strong>fett</strong> &lt;script&gt;alert(1)&lt;/script&gt;</p>\n',
    )
  })

  it('opens links in a new tab and drops script links', async () => {
    const render = await markdownRenderer()
    expect(render('[Doku](https://example.com)')).toContain(
      '<a href="https://example.com" target="_blank" rel="noopener noreferrer">Doku</a>',
    )
    expect(render('[x](javascript:alert(1))')).not.toContain('<a')
  })
})

describe('firstLine', () => {
  it('takes the first non-empty line as plain text', () => {
    expect(firstLine('\n\n## **Server** getauscht\nmehr')).toBe('Server getauscht')
    expect(firstLine('- [x] [USV](https://example.com) geprüft')).toBe('USV geprüft')
    expect(firstLine('1. `RAM` _tauschen_')).toBe('RAM tauschen')
    expect(firstLine('')).toBe('')
    expect(firstLine('a'.repeat(600))).toHaveLength(500)
  })
})
