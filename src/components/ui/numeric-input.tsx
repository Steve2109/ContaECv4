'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Input } from '@/components/ui/input';

/**
 * NumericInput — Input numérico que acepta punto O coma como separador decimal.
 *
 * Resuelve: con type="number" nativo, si el usuario escribe un punto, el
 * navegador lo interpreta como decimal incompleto y el componente React
 * recibe "" o "NaN", provocando que el campo se borre o reinicie a 0.
 *
 * El formateo visual (thousands separator, decimal fix) solo se aplica al
 * pierder el foco (blur), para no interrumpir la escritura del usuario.
 */
interface NumericInputProps {
  id?: string;
  ref?: React.Ref<HTMLInputElement>;
  value: number | string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChange: (...args: any[]) => void; // Accepts both (e) => e.target.value and (v) => v
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  decimals?: number;
  thousands?: boolean;
  integer?: boolean;
  min?: number;
  max?: number;
  maxLength?: number;
  style?: React.CSSProperties;
}

function formatDisplay(value: number, decimals: number, thousands: boolean): string {
  if (value === null || value === undefined || isNaN(value)) return '';
  if (thousands) {
    return value.toLocaleString('es-EC', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
  const fixed = value.toFixed(decimals);
  return fixed.replace('.', ',');
}

/**
 * Parse raw display text (with commas as decimal separators) back to a number.
 */
function parseDisplayText(raw: string): number | null {
  if (!raw || raw === '-' || raw === ',') return null;
  const normalized = raw.replace(/,/g, '.');
  const parsed = parseFloat(normalized);
  return isNaN(parsed) ? null : parsed;
}

export function NumericInput({
  id,
  ref,
  value,
  onChange,
  onKeyDown,
  onBlur: onBlurProp,
  placeholder,
  className,
  disabled,
  autoFocus,
  decimals = 2,
  thousands = true,
  integer = false,
  min = -Infinity,
  max = Infinity,
  maxLength,
  style,
}: NumericInputProps) {
  const maxDecimals = integer ? 0 : decimals;

  const numericValue = typeof value === 'string' ? parseFloat(value) || 0 : value;

  // Track whether the current text was set by user typing vs external value change
  const isTypingRef = useRef(false);

  const [text, setText] = useState<string>(() =>
    numericValue ? formatDisplay(numericValue, maxDecimals, thousands) : ''
  );

  // Only sync text from external value when we're NOT in the middle of typing
  useEffect(() => {
    if (isTypingRef.current) return;
    const display = numericValue ? formatDisplay(numericValue, maxDecimals, thousands) : '';
    setText(display);
  }, [numericValue, maxDecimals, thousands]);

  const callOnChange = useCallback(
    (num: number) => {
      if (!onChange) return;
      try {
        const src = onChange.toString();
        if (src.includes('.target')) {
          // Legacy handler: (e) => setForm({...form, X: Number(e.target.value)})
          const syntheticEvent = {
            target: { value: String(num) },
          } as React.ChangeEvent<HTMLInputElement>;
          onChange(syntheticEvent);
        } else {
          // Modern handler: (v) => setForm({...form, X: v})
          onChange(num);
        }
      } catch {
        onChange(num);
      }
    },
    [onChange]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      let raw = e.target.value;

      raw = raw.replace(/\./g, ',');

      if (integer) {
        raw = raw.replace(/[^\d-]/g, '');
        if (raw.startsWith('-') && raw.indexOf('-') !== 0) {
          raw = raw.replace(/-/g, '');
          raw = '-' + raw;
        }
      } else {
        raw = raw.replace(/[^\d,-]/g, '');
        if (raw.includes('-')) {
          raw = '-' + raw.replace(/-/g, '');
        }
        const firstComma = raw.indexOf(',');
        if (firstComma !== -1) {
          const intPart = raw.slice(0, firstComma);
          let decPart = raw.slice(firstComma + 1);
          decPart = decPart.slice(0, maxDecimals);
          raw = intPart + ',' + decPart;
        }
      }

      // Mark that we're typing so the useEffect doesn't overwrite our text
      isTypingRef.current = true;
      setText(raw);

      // Parse and emit the numeric value for state updates
      const parsed = parseDisplayText(raw);
      if (parsed !== null) {
        const clamped = Math.min(max, Math.max(min, parsed));
        callOnChange(clamped);
      }

      // Allow the next useEffect cycle to check isTypingRef before clearing it
      // We use a micro-task so the effect runs before we clear the flag
      Promise.resolve().then(() => {
        isTypingRef.current = false;
      });
    },
    [callOnChange, maxDecimals, integer, min, max]
  );

  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement>) => {
      // Format the display value when losing focus
      const display = numericValue ? formatDisplay(numericValue, maxDecimals, thousands) : '';
      setText(display);
      onBlurProp?.(e);
    },
    [numericValue, maxDecimals, thousands, onBlurProp]
  );

  return (
    <Input
      ref={ref}
      id={id}
      inputMode={integer ? 'numeric' : 'decimal'}
      type="text"
      value={text}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyDown={onKeyDown}
      placeholder={placeholder ?? (integer ? '0' : '0,00')}
      className={className}
      disabled={disabled}
      autoFocus={autoFocus}
      style={style}
      maxLength={maxLength}
      autoComplete="off"
    />
  );
}
