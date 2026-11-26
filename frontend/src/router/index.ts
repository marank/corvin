import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { clearFormErrors } from '../composables/formErrors'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('../layouts/AppShell.vue'),
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
        {
          path: 'customers',
          name: 'customers',
          component: () => import('../views/customers/CustomerListView.vue'),
        },
        {
          path: 'customers/:id',
          name: 'customer-detail',
          component: () => import('../views/customers/CustomerDetailView.vue'),
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('../views/projects/ProjectListView.vue'),
        },
        {
          path: 'projects/:id',
          name: 'project-detail',
          component: () => import('../views/projects/ProjectDetailView.vue'),
        },
        { path: 'tasks', name: 'tasks', component: () => import('../views/TasksView.vue') },
        { path: 'time', name: 'time', component: () => import('../views/TimeTrackingView.vue') },
        {
          path: 'visits',
          name: 'visits',
          component: () => import('../views/visits/VisitListView.vue'),
        },
        {
          path: 'visits/:id',
          name: 'visit-detail',
          component: () => import('../views/visits/VisitDetailView.vue'),
        },
        {
          path: 'contracts',
          name: 'contracts',
          component: () => import('../views/contracts/ContractListView.vue'),
        },
        {
          path: 'contracts/:id',
          name: 'contract-detail',
          component: () => import('../views/contracts/ContractDetailView.vue'),
        },
        {
          path: 'invoices',
          name: 'invoices',
          component: () => import('../views/invoices/InvoiceListView.vue'),
        },
        {
          path: 'invoices/new',
          name: 'invoice-new',
          component: () => import('../views/invoices/InvoiceCreateView.vue'),
        },
        {
          // A draft on the create page (see InvoiceCreateView).
          path: 'invoices/:id/edit',
          name: 'invoice-edit',
          component: () => import('../views/invoices/InvoiceCreateView.vue'),
        },
        {
          path: 'invoices/:id',
          name: 'invoice-detail',
          component: () => import('../views/invoices/InvoiceDetailView.vue'),
        },
        {
          path: 'templates',
          name: 'templates',
          component: () => import('../views/templates/TemplateListView.vue'),
        },
        {
          path: 'templates/:id',
          name: 'designer',
          component: () => import('../views/InvoiceDesignerView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/settings/SettingsProfileView.vue'),
        },
        {
          path: 'settings/security',
          name: 'settings-security',
          component: () => import('../views/settings/SettingsSecurityView.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.checked) await auth.check()
  if (!to.meta.public && !auth.user) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.name === 'login' && auth.user) return { name: 'dashboard' }
})

// Errors belong to the form on the page that was left.
router.afterEach(() => clearFormErrors())

export default router
