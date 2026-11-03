import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

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
  // Blue to match the logo (Aura defaults to emerald).
  semantic: {
    primary: {
      50: '{blue.50}',
      100: '{blue.100}',
      200: '{blue.200}',
      300: '{blue.300}',
      400: '{blue.400}',
      500: '{blue.500}',
      600: '{blue.600}',
      700: '{blue.700}',
      800: '{blue.800}',
      900: '{blue.900}',
      950: '{blue.950}',
    },
  },
  components: {
    // Compact tables: quiet header, ~38px rows. Font size, casing and the
    // sort-icon visibility live in style.css (no tokens for those).
    datatable: {
      headerCell: {
        padding: '0.5rem 0.75rem',
        color: '{text.muted.color}',
        hoverColor: '{text.color}',
        selectedColor: '{primary.color}',
      },
      columnTitle: { fontWeight: '500' },
      bodyCell: { padding: '0.5rem 0.75rem' },
      sortIcon: { size: '0.75rem' },
      colorScheme: {
        light: {
          headerCell: {
            background: '{surface.50}',
            hoverBackground: '{surface.100}',
            selectedBackground: '{surface.50}',
          },
          row: { hoverBackground: '{surface.50}' },
          bodyCell: { borderColor: '{surface.100}' },
        },
        dark: {
          headerCell: {
            background: '{surface.950}',
            hoverBackground: '{surface.800}',
            selectedBackground: '{surface.950}',
          },
          row: { hoverBackground: '{surface.800}' },
          bodyCell: { borderColor: '{surface.800}' },
        },
      },
    },
  },
})
