import { Noto_Sans } from 'next/font/google';
import '@ama-pt/agora-design-system/artifacts/dist/tailwind.css';
import './globals.css';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';

const notoSans = Noto_Sans({
  variable: '--font-noto-sans',
  subsets: ['latin'],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
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
