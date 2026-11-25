import type { Config } from 'tailwindcss'

/**
 * Tokens del diseño de Canva:
 *  - oscuro principal  #0a2328
 *  - verde acción      #15803d
 *  - tarjetas blancas con bordes suaves
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#0a2328',
          darkAlt: '#103138',
          action: '#15803d',
          actionHover: '#166534',
          actionSoft: '#dcfce7',
          muted: '#5b6b70',
          line: '#e3e8ea',
          bg: '#f5f7f8',
        },
      },
      borderRadius: {
        card: '14px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(10,35,40,.06), 0 8px 24px -12px rgba(10,35,40,.18)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
