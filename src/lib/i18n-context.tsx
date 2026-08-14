'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { getLocale, setLocale, t as translate, LOCALES, getLocaleLabel } from './i18n';
import type { Locale } from './i18n';
import { translateToEnglish, isEnglishLocale } from './runtime-translator';

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  locales: typeof LOCALES;
  getLocaleLabel: (locale: Locale) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

// Nodos cuyo contenido no debe traducirse
const SKIP_TAGS = new Set([
  'SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'SELECT', 'OPTION', 'CODE', 'PRE', 'KBD', 'SVG',
]);

function shouldSkip(node: Node): boolean {
  const parent = node.parentElement;
  if (!parent) return true;
  if (SKIP_TAGS.has(parent.tagName)) return true;
  const attr = (parent.getAttribute && parent.getAttribute('data-no-translate')) || '';
  if (attr) return true;
  let el: HTMLElement | null = parent;
  let depth = 0;
  while (el && depth < 4) {
    if (SKIP_TAGS.has(el.tagName)) return true;
    if (el.hasAttribute && el.hasAttribute('contenteditable')) return true;
    el = el.parentElement;
    depth++;
  }
  return false;
}

// Estado del traductor guardado en el propio nodo de texto:
//  - __rtEs: texto original en español (para restaurar)
//  - __rtEn: traducción aplicada (para detectar re-renders de React)
type RtText = Text & { __rtEs?: string; __rtEn?: string };

function translateTextNode(node: Text): void {
  const text = node.nodeValue ?? '';
  if (!text.trim()) return;
  if (text.length > 500) return; // textos muy largos (cuerpos de correo) se omiten
  if (!node.parentElement) return;

  const rt = node as RtText;
  if (rt.__rtEn !== undefined) {
    // Nodo ya traducido por nosotros.
    if (text === rt.__rtEn) return; // sigue mostrando el inglés: nada que hacer
    // El texto cambió (React re-escribió el original en español): re-traducir.
    rt.__rtEs = undefined;
    rt.__rtEn = undefined;
  }

  const translated = translateToEnglish(text);
  if (translated === text) return;

  rt.__rtEs = text;
  rt.__rtEn = translated;
  node.nodeValue = translated;
}

function restoreTextNode(node: Text): void {
  const rt = node as RtText;
  if (rt.__rtEs !== undefined) {
    node.nodeValue = rt.__rtEs;
  }
  rt.__rtEs = undefined;
  rt.__rtEn = undefined;
}

function scanTranslate(root: Node): void {
  if (root.nodeType === Node.TEXT_NODE) {
    translateTextNode(root as Text);
    return;
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node: Node) {
      return shouldSkip(node) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    },
  });
  const nodes: Text[] = [];
  let n: Node | null = walker.nextNode();
  while (n) {
    nodes.push(n as Text);
    n = walker.nextNode();
  }
  for (const tn of nodes) translateTextNode(tn);
}

function scanRestore(root: Node): void {
  if (root.nodeType === Node.TEXT_NODE) {
    restoreTextNode(root as Text);
    return;
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let n: Node | null = walker.nextNode();
  while (n) {
    nodes.push(n as Text);
    n = walker.nextNode();
  }
  for (const tn of nodes) restoreTextNode(tn);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === 'undefined') return 'es_EC';
    return getLocale();
  });
  const localeRef = useRef(locale);
  localeRef.current = locale;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Escucha cambios desde otras pestañas
    const handler = (e: StorageEvent) => {
      if (e.key === 'contaec_locale' && e.newValue) {
        if (e.newValue === 'es_EC' || e.newValue === 'en_US') {
          setLocaleState(e.newValue as Locale);
        }
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  // Traductor en tiempo real: observa el DOM y traduce el texto visible
  useEffect(() => {
    if (typeof document === 'undefined') return;

    const apply = () => {
      // Lee el idioma real (los componentes pueden escribirlo en localStorage
      // sin pasar por el estado del provider, p. ej. el selector del dashboard).
      const current = getLocale();
      localeRef.current = current;
      if (current === 'es_EC') {
        scanRestore(document.body);
      } else if (isEnglishLocale(current)) {
        scanTranslate(document.body);
      }
    };

    const debounced = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(apply, 80);
    };

    apply();
    const observer = new MutationObserver(debounced);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    return () => {
      observer.disconnect();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [locale]);

  const changeLocale = useCallback((newLocale: Locale) => {
    setLocale(newLocale);
    setLocaleState(newLocale);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      return translate(key, params);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [locale]
  );

  return (
    <I18nContext.Provider
      value={{
        locale,
        setLocale: changeLocale,
        t,
        locales: LOCALES,
        getLocaleLabel,
      }}
    >
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return ctx;
}
