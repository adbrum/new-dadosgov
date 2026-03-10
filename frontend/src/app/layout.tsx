import type { Metadata } from 'next';
import { Noto_Sans } from 'next/font/google';
import '@ama-pt/agora-design-system/artifacts/dist/tailwind.css';
import './globals.css';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { siteConfig } from '@/config/site';

const notoSans = Noto_Sans({
  variable: '--font-noto-sans',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: siteConfig.title,
    template: `%s | ${siteConfig.title}`,
  },
  description: siteConfig.description,
  icons: {
    icon: '/favicon.svg',
  },
  openGraph: {
    title: siteConfig.title,
    description: siteConfig.description,
    url: siteConfig.url,
    siteName: siteConfig.name,
    locale: siteConfig.locale,
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt">
      <body className={`${notoSans.variable} antialiased font-sans`}>
        <div className="min-h-screen w-full mx-auto flex flex-col">
          <Header />
          <div className="grow">{children}</div>
          <Footer />
        </div>
      </body>
    </html>
  );
}
