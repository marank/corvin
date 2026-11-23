import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVueA11y from 'eslint-plugin-vuejs-accessibility'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import comments from '@eslint-community/eslint-plugin-eslint-comments'
import vitest from '@vitest/eslint-plugin'
import sonarjs from 'eslint-plugin-sonarjs'

// Import boundaries. Later blocks replace the rule's options, so each lists every pattern that applies.
// The raw HTTP client stays inside src/api/; everything else calls the area functions in src/api/index.ts
// (ApiError and the Page type may still be imported from the client).
const rawClient = {
  regex: '(^|/)api/client$',
  importNames: ['api'],
  message: 'Call the area functions in src/api/index.ts instead of the raw client.',
}
// A page is the end of the line: nothing imports a view except the router.
const views = {
  regex: '(^|/)views/|(^|/)[A-Z]\\w*View\\.vue$',
  caseSensitive: true,
  message:
    'Shared code and other views must not depend on a view; move the shared part to components/ or composables/.',
}
// Pure helpers: no components, no API calls (the generated schema types are fine).
const impure = {
  regex: '(^|/)(components|stores|composables)/|(^|/)api(/(index|client))?$',
  message: 'utils stay pure: no components, stores, composables or API calls.',
}

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores(['**/dist/**', '**/coverage/**', 'src/api/schema.d.ts']),

  pluginVue.configs['flat/strongly-recommended'],
  ...pluginVueA11y.configs['flat/recommended'],
  vueTsConfigs.recommendedTypeChecked,
  skipFormatting,

  // No silenced checks: every disable names its rules and says why; unused ones fail.
  { name: 'project/linter', linterOptions: { reportUnusedDisableDirectives: 'error' } },
  {
    name: 'project/no-silencing',
    files: ['src/**/*.{ts,tsx,vue}'],
    plugins: { '@eslint-community/eslint-comments': comments },
    rules: {
      '@eslint-community/eslint-comments/no-unlimited-disable': 'error',
      '@eslint-community/eslint-comments/require-description': 'error',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        { 'ts-expect-error': 'allow-with-description' },
      ],
    },
  },
  // Tests that test: every test asserts, no `.only` or skipped test is committed.
  {
    name: 'project/tests',
    files: ['src/**/*.{test,spec}.ts'],
    plugins: { vitest },
    rules: {
      'vitest/expect-expect': 'error',
      'vitest/no-focused-tests': 'error',
      'vitest/no-disabled-tests': 'error',
    },
  },
  // PrimeVue renders the real <input> inside its components, so a <label> around or `for` one of
  // them labels a control. AppFormField names its control through the group's aria-labelledby.
  {
    name: 'project/a11y',
    files: ['src/**/*.vue'],
    rules: {
      'vuejs-accessibility/label-has-for': [
        'error',
        {
          required: { some: ['nesting', 'id'] },
          controlComponents: ['Checkbox', 'InputText', 'Password', 'InputNumber', 'Select'],
        },
      ],
      'vuejs-accessibility/form-control-has-label': [
        'error',
        { labelComponents: ['AppFormField'] },
      ],
      // AppLogo renders the app name as text.
      'vuejs-accessibility/heading-has-content': ['error', { accessibleChildren: ['AppLogo'] }],
    },
  },
  // Limits on tangle, not on length (no max-lines / max-statements).
  {
    name: 'project/readability',
    files: ['src/**/*.{ts,tsx,vue}'],
    plugins: { sonarjs },
    rules: {
      complexity: ['error', 15],
      'sonarjs/cognitive-complexity': ['error', 15],
      'max-depth': ['error', 4],
      '@typescript-eslint/no-unnecessary-condition': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      // Unescaped HTML runs whatever a user typed (XSS). A real exception gets
      // `eslint-disable-next-line vue/no-v-html -- reason`.
      'vue/no-v-html': 'error',
      'vue/no-unused-properties': [
        'error',
        { groups: ['props', 'data', 'computed', 'methods', 'setup'] },
      ],
      'no-restricted-imports': ['error', { patterns: [rawClient, views] }],
    },
  },
  { name: 'project/api', files: ['src/api/**'], rules: { 'no-restricted-imports': 'off' } },
  // Tests mount the views they test, inside small host components of their own.
  {
    name: 'project/test-imports',
    files: ['src/__tests__/**'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [rawClient] }],
      'vue/one-component-per-file': 'off',
    },
  },
  // The router is the one place that maps URLs to views.
  {
    name: 'project/router',
    files: ['src/router/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [rawClient] }] },
  },
  {
    name: 'project/utils',
    files: ['src/utils/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [rawClient, views, impure] }] },
  },
)
