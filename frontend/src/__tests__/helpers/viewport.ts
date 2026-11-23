// jsdom has no matchMedia. AppDataTable asks for "(min-width: 768px)" to choose between the
// table (desktop) and the card list (mobile); tests pick one per mount.
let desktop = true

export function setViewport(kind: 'desktop' | 'mobile') {
  desktop = kind === 'desktop'
}

window.matchMedia = (query: string) =>
  ({
    matches: /min-width/.test(query) ? desktop : false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }) as MediaQueryList
