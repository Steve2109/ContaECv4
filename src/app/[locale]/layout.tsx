import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import "../globals.css";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "@/components/providers";

export const dynamic = 'force-dynamic';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ContaEC - Contabilidad y Facturacion Electronica Ecuador",
  description:
    "Sistema de contabilidad y facturacion electronica para Ecuador. Cumpla con las normativas del SRI de manera simple y eficiente.",
  keywords: [
    "ContaEC",
    "contabilidad Ecuador",
    "facturacion electronica",
    "SRI",
    "comprobantes electronicos",
    "Ecuador",
    "contabilidad",
    "facturacion",
  ],
  authors: [{ name: "T&M Technology Ec" }],
  icons: {
    icon: [
      { url: "/logo.svg", type: "image/svg+xml" },
      { url: "/logo.svg", rel: "icon", type: "image/svg+xml" },
      { url: "/logo.svg", rel: "apple-touch-icon" },
    ],
    shortcut: "/logo.svg",
    apple: { url: "/logo.svg" },
  },
  openGraph: {
    title: "ContaEC - Contabilidad y Facturacion Electronica",
    description:
      "Sistema de contabilidad y facturacion electronica para Ecuador",
    type: "website",
    images: [
      {
        url: "/logo.svg",
        width: 600,
        height: 500,
        alt: "ContaEC Logo",
      },
    ],
  },
};

export default async function LocaleLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <NextIntlClientProvider messages={messages}>
          <Providers>
            {children}
            <Toaster />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
