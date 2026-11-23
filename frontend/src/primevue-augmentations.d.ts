// Gaps in PrimeVue 4's type declarations, filled so strict template checking matches what the
// components do at runtime.
import 'primevue/steps'
import 'primevue/select'
import 'primevue/checkbox'
import 'primevue/button'

declare module 'primevue/steps' {
  // Steps emits these (see its `emits` option), but declares an empty emits interface.
  interface StepsEmitsOptions {
    'update:activeStep'(index: number): void
  }
}

// Vue matches the `aria-label` attribute to the camelCase `ariaLabel` prop these components declare;
// vue-tsc checks `aria-*` attributes under their HTML name, so declare that spelling too.
declare module 'primevue/select' {
  interface SelectProps {
    'aria-label'?: string | undefined
  }
}

declare module 'primevue/checkbox' {
  interface CheckboxProps {
    'aria-label'?: string | undefined
  }
}

// `as="a"` renders the button as a link; its link attributes fall through to the <a>.
declare module 'primevue/button' {
  interface ButtonProps {
    href?: string | undefined
    target?: string | undefined
    download?: boolean | string | undefined
  }
}
