// Markdown for free-text reports (time entries). Loaded on first use, so the parser is not
// part of the main bundle. Raw HTML in the source is escaped (`html: false`) and link targets
// are checked by markdown-it (no javascript: or data: URLs), so the output is safe for v-html.

type Render = (source: string) => string

let renderer: Promise<Render> | undefined

export function markdownRenderer(): Promise<Render> {
  renderer ??= import('markdown-it').then(({ default: MarkdownIt }) => {
    const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
    // Links leave the app in a new tab.
    md.renderer.rules.link_open = (tokens, index, options, _env, self) => {
      tokens[index]!.attrSet('target', '_blank')
      tokens[index]!.attrSet('rel', 'noopener noreferrer')
      return self.renderToken(tokens, index, options)
    }
    return (source: string) => md.render(source)
  })
  return renderer
}

// The first line of a Markdown text as plain text: the short form of a report.
export function firstLine(source: string, maxLength = 500): string {
  const line =
    source
      .split('\n')
      .map((text) => text.trim())
      .find((text) => text.length > 0) ?? ''
  const plain = line
    .replace(/^(#{1,6}\s+|>\s*|[-*+]\s+(\[[ xX]\]\s+)?|\d+[.)]\s+)/, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/(\*\*|__|\*|_|~~|`)/g, '')
    .trim()
  return plain.slice(0, maxLength)
}
