'use client';
import { useEffect, useRef } from 'react';

/** 모달/드로어용 focus trap.
 *  - 컨테이너 ref 반환, 오픈 시 첫 focusable 요소로 포커스
 *  - TAB / SHIFT+TAB 시 순환 처리
 *  - 언마운트 시 원래 포커스 요소로 복귀
 */
const SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function useFocusTrap<T extends HTMLElement>(active: boolean = true) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    if (!active || !ref.current) return;
    const container = ref.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;

    const focusables = () =>
      Array.from(container.querySelectorAll<HTMLElement>(SELECTOR)).filter(
        (el) => el.offsetParent !== null
      );

    // 오픈 시 첫 요소로 포커스 (autoFocus가 있는 요소 우선)
    const autoFocused = container.querySelector<HTMLElement>('[data-autofocus]') ||
      (container.querySelector('input[autofocus]') as HTMLElement | null) ||
      focusables()[0];
    autoFocused?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Tab') return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const cur = document.activeElement as HTMLElement;

      if (e.shiftKey) {
        if (cur === first || !container.contains(cur)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (cur === last || !container.contains(cur)) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    container.addEventListener('keydown', onKeyDown);
    return () => {
      container.removeEventListener('keydown', onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [active]);

  return ref;
}
