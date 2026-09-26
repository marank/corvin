import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'

// Flat theme. Square corners are enforced globally via CSS (style.css);
// the preset tunes colors + tokens. `borderRadius` zeroed defensively.
export const FlatPreset = definePreset(Aura, {
  primitive: {
    borderRadius: {
      none: '0',
      xs: '0',
      sm: '0',
      md: '0',
      lg: '0',
      xl: '0',
    },
  },
})
