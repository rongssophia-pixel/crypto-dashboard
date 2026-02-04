/**
 * Interval Hook
 * Run a callback at a fixed interval
 */

import { useEffect, useRef } from 'react';

export function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef<() => void>(callback);

  // Remember the latest callback
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval
  useEffect(() => {
    if (delay === null) {
      return;
    }

    function tick() {
      savedCallback.current?.();
    }

    const id = setInterval(tick, delay);
    return () => clearInterval(id);
  }, [delay]);
}






