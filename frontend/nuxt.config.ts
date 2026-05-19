// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxtjs/mdc',
    '@nuxthub/core',
    'nuxt-auth-utils',
    'nuxt-charts',
    'nuxt-csurf',
    '@nuxt/image'
  ],

  // App is mounted as an IIS Application under https://www.dpsa.gov.za/chatbot/.
  // baseURL controls asset URL generation and server route registration so
  // that requests like /chatbot/api/chats reach Nitro correctly.
  app: {
    baseURL: '/chatbot/'
  },

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  mdc: {
    headings: {
      anchorLinks: false
    },
    highlight: {
      // noApiRoute: true
      shikiEngine: 'javascript'
    }
  },

  experimental: {
    viewTransition: true
  },

  compatibilityDate: '2024-07-11',

  nitro: {
    experimental: {
      openAPI: true
    }
  },

  hub: {
    db: 'sqlite',
    blob: false
  },

  runtimeConfig: {
    public: {
      // Server-side only: Nitro API routes call FastAPI via $fetch(`${apiBase}/chat`).
      // The browser never touches this URL directly. Default targets loopback on the
      // same IIS machine. Override at runtime via NUXT_PUBLIC_API_BASE if needed.
      apiBase: 'http://127.0.0.1:8080'
    }
  },

  vite: {
    server: {
      allowedHosts: true
    },
    optimizeDeps: {
      include: [
        'striptags',
        'motion-v'
      ]
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})