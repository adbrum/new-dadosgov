import type { Config } from 'tailwindcss';
import { AgoraTailwindConfig } from '@ama-pt/agora-design-system';

const config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './node_modules/@ama-pt/agora-design-system/artifacts/dist/**/*.{js,mjs}',
  ],
  theme: {
    ...AgoraTailwindConfig.theme,
    extend: {
      colors: {
        'accent-light': '#F7F7FF',
        'brand-blue-dark': '#021C51',
        'brand-blue-primary': '#0C02CB',
        'brand-blue-secondary': '#050157',
        'gray-medium': '#64718B',
      },
      fontSize: {
        '24': '24px',
        '32': '32px',
        '40': '40px',
      },
      spacing: {
        '32': '32px',
        '64': '64px',
        '24': '24px',
        '40': '40px',
      },
      fontFamily: {
        sans: ['var(--font-noto-sans)', 'sans-serif'],
      },
    },
  },
  plugins: AgoraTailwindConfig.plugins,
  safelist: [
    ...(AgoraTailwindConfig.safelist || []),
    '!hidden',
    '!block',
    '!flex',
  ] as any[],
  corePlugins: {
    preflight: false,
  },
};

export default config;
