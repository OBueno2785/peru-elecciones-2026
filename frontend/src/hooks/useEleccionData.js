import { useState, useEffect, useRef, useCallback } from 'react';

const ENDPOINTS = {
  'presidencial':    '/api/presidencial',
  'senado-regional': '/api/senado-regional',
  'diputados':       '/api/diputados',
};

const POLL_INTERVAL = 5 * 60 * 1000; // 5 minutos

export function useEleccionData(tipo) {
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const timerRef = useRef(null);

  const fetchData = useCallback(async (isBackground = false) => {
    if (!tipo) return;
    if (isBackground) setRefreshing(true);
    else { setLoading(true); setError(null); }

    try {
      const r = await fetch(ENDPOINTS[tipo]);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setData(d);
      setLastUpdate(new Date());
      setError(null);
    } catch (e) {
      if (!isBackground) setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [tipo]);

  // Carga inicial y cuando cambia el tipo
  useEffect(() => {
    setData(null);
    fetchData(false);
  }, [tipo]);

  // Polling en segundo plano cada 5 minutos
  useEffect(() => {
    timerRef.current = setInterval(() => fetchData(true), POLL_INTERVAL);
    return () => clearInterval(timerRef.current);
  }, [fetchData]);

  return { data, loading, error, refreshing, lastUpdate, refresh: () => fetchData(true) };
}
