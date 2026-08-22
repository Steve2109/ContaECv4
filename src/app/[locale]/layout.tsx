import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "@/components/providers";

export const dynamic = 'force-dynamic';

export default async function LocaleLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const messages = await getMessages();

  // NOTE: <html> and <body> are rendered by the root layout (app/layout.tsx).
  // This layout provides i18n + theme providers.
  return (
    <NextIntlClientProvider messages={messages}>
      <Providers>
        {children}
        <Toaster />
      </Providers>
    </NextIntlClientProvider>
  );
}
