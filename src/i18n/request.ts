import { getRequestConfig } from 'next-intl/server';
import { locales, defaultLocale, type Locale } from '../i18n-config';

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;

  // Validate against supported locales (next-intl 3.22+ migration)
  if (!locale || !locales.includes(locale as Locale)) {
    locale = defaultLocale;
  }

  return {
    // next-intl 3.22+ expects the resolved locale to be returned explicitly
    locale,

    // Loads the `messages/[locale].json` file
    messages: (await import(`../../messages/${locale}.json`)).default,

    // Timezone for date formatting
    timeZone: 'America/Guayaquil',

    // Custom formatters for locale-specific formatting
    formats: {
      dateTime: {
        short: {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric'
        },
        long: {
          day: '2-digit',
          month: 'long',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        }
      },
      number: {
        currency: {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        }
      }
    }
  };
});
