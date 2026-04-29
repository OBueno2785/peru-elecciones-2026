import { useEffect, useState, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts';
import { fmtPct } from '../utils';

const POLL_INTERVAL = 5 * 60 * 1000;

const RANGOS = [
  { id: '6h',  label: 'Últimas 6h',  ms: 6  * 60 * 60 * 1000 },
  { id: '12h', label: 'Últimas 12h', ms: 12 * 60 * 60 * 1000 },
  { id: '24h', label: 'Últimas 24h', ms: 24 * 60 * 60 * 1000 },
  { id: 'all', label: 'Todo',        ms: null },
];

function abrev(nombre) {
  if (!nombre) return '';
  const MAP = {
    'FUERZA POPULAR':            'Fuerza Popular',
    'RENOVACIÓN POPULAR':        'Renovación Popular',
    'PARTIDO DEL BUEN GOBIERNO': 'Buen Gobierno',
    'JUNTOS POR EL PERÚ':        'Juntos por el Perú',
    'PARTIDO CÍVICO OBRAS':      'Cívico Obras',
    'PARTIDO PAÍS PARA TODOS':   'País para Todos',
    'AHORA NACIÓN - AN':         'Ahora Nación',
  };
  const upper = nombre.toUpperCase();
  const key = Object.keys(MAP).find(k => upper.includes(k));
  if (key) return MAP[key];
  const words = nombre.split(' ');
  return words.length > 3 ? words.slice(0, 3).join(' ') + '…' : nombre;
}

function formatHora(ts, incluirFecha = false) {
  try {
    const d = new Date(ts);
    if (incluirFecha) {
      return d.toLocaleString('es-PE', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    }
    return d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  } catch { return String(ts); }
}

function TooltipPersonalizado({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const sorted = [...payload].sort((a, b) => b.value - a.value);
  const actas  = payload[0]?.payload?.actas;
  const esLive = payload[0]?.payload?.esLive;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs min-w-44">
      <div className="flex justify-between mb-2">
        <span className="font-bold text-gray-600">
          {label}
          {esLive && <span className="ml-1 text-green-500 font-bold">● EN VIVO</span>}
        </span>
        {actas != null && (
          <span className="text-blue-500 font-medium">{fmtPct(actas)} actas</span>
        )}
      </div>
      {sorted.map((p, i) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-3 mb-0.5">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-gray-400 w-3">#{i + 2}</span>
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: p.color }} />
            <span className="text-gray-700">{abrev(p.name)}</span>
          </div>
          <span className="font-bold tabular-nums" style={{ color: p.color }}>
            {fmtPct(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SeccionCarrera() {
  const [snapshots,   setSnapshots]   = useState([]);
  const [liveTop,     setLiveTop]     = useState(null);
  const [liveActas,   setLiveActas]   = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [lastUpdate,  setLastUpdate]  = useState(null);
  const [rango,       setRango]       = useState('24h');

  useEffect(() => {
    let mounted = true;

    async function fetchAll() {
      try {
        const [rH, rP] = await Promise.all([
          fetch('/api/historial'),
          fetch('/api/presidencial'),
        ]);
        if (!rH.ok || !rP.ok) throw new Error('Error de red');
        const dH = await rH.json();
        const dP = await rP.json();
        if (!mounted) return;
        setSnapshots(Array.isArray(dH.snapshots) ? dH.snapshots : []);
        setLiveTop(Array.isArray(dP?.nacional?.top) ? dP.nacional.top : null);
        // Publicado por ONPE = contabilizadas + en JEE
        const totales = dP?.nacional?.totales;
        setLiveActas(totales ? ((totales.actasContabilizadas ?? 0) + (totales.actasEnviadasJee ?? 0)) : null);
        setLastUpdate(new Date());
      } catch (e) {
        if (mounted) setError(e.message);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchAll();
    const t = setInterval(fetchAll, POLL_INTERVAL);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  // ── Derivar datos siempre (antes de cualquier return) ──────────────────────

  const ultimo = snapshots.length > 0 ? snapshots[snapshots.length - 1] : null;

  // Partidos a mostrar en el gráfico: fijos desde el último snapshot para consistencia
  const enCarrera = useMemo(
    () => (ultimo?.candidatos ? ultimo.candidatos.slice(1, 7) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ultimo?.ts]   // solo recalcular si llega un snapshot nuevo
  );

  // Posiciones en vivo (preferir liveTop, fallback al último snapshot)
  const candidatosActuales = useMemo(
    () => (liveTop && liveTop.length > 0 ? liveTop.slice(0, 8) : (ultimo?.candidatos ?? [])),
    [liveTop, ultimo]
  );

  const lider         = candidatosActuales.length > 0 ? candidatosActuales[0] : null;
  const enCarreraVivo = candidatosActuales.slice(1, 7);
  const actasActuales = liveActas ?? ultimo?.actas ?? null;
  const dif           = enCarreraVivo.length >= 2
    ? (enCarreraVivo[0].pct - enCarreraVivo[1].pct).toFixed(2) : null;

  // Snapshots filtrados por rango
  const snapshotsFiltrados = useMemo(() => {
    const cfg = RANGOS.find(r => r.id === rango);
    if (!cfg?.ms) return snapshots;
    const corte = Date.now() - cfg.ms;
    return snapshots.filter(s => new Date(s.ts).getTime() >= corte);
  }, [snapshots, rango]);

  // ¿Los datos abarcan más de un día?
  const spanMultiDia = useMemo(() => {
    if (snapshotsFiltrados.length < 2) return false;
    const d0 = new Date(snapshotsFiltrados[0].ts).toDateString();
    const dN = new Date(snapshotsFiltrados[snapshotsFiltrados.length - 1].ts).toDateString();
    return d0 !== dN;
  }, [snapshotsFiltrados]);

  // Datos para recharts
  const chartData = useMemo(() => {
    if (enCarrera.length === 0) return [];

    const puntos = snapshotsFiltrados.map(snap => {
      const pt = { label: formatHora(snap.ts, spanMultiDia), actas: snap.actas, esLive: false };
      for (const c of enCarrera) {
        const found = snap.candidatos?.find(x => x.partido === c.partido);
        pt[c.partido] = found ? found.pct : null;
      }
      return pt;
    });

    // Añadir punto en vivo si difiere del último guardado
    if (liveTop && liveActas != null) {
      const last = puntos[puntos.length - 1];
      const liveR  = Math.round(liveActas  * 100) / 100;
      const savedR = last ? Math.round(last.actas * 100) / 100 : null;
      if (liveR !== savedR) {
        const pt = {
          label: formatHora(new Date().toISOString(), spanMultiDia) + ' ●',
          actas: liveR,
          esLive: true,
        };
        for (const c of enCarrera) {
          const found = liveTop.find(x => x.partido === c.partido);
          pt[c.partido] = found ? found.pct : null;
        }
        puntos.push(pt);
      }
    }
    return puntos;
  }, [enCarrera, snapshotsFiltrados, spanMultiDia, liveTop, liveActas]);

  // ── Early returns (siempre después de todos los hooks) ─────────────────────

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-red-500 text-sm px-8 text-center">
        Error cargando datos: {error}
      </div>
    );
  }

  if (!ultimo) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-center px-8">
        <div>
          <p className="text-gray-500 font-medium">Sin datos históricos aún</p>
          <p className="text-gray-400 text-sm mt-1">Los datos se registrarán en el próximo refresco de ONPE (cada 5 min).</p>
        </div>
      </div>
    );
  }

  const soloUnPunto = chartData.length < 2;

  return (
    <div className="flex-1 flex flex-col overflow-auto bg-gray-50">

      {/* Cabecera */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Carrera por el 2° puesto</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Evolución real · {snapshots.length} actualización{snapshots.length !== 1 ? 'es' : ''} de ONPE registrada{snapshots.length !== 1 ? 's' : ''}
              {lastUpdate && ` · última consulta ${lastUpdate.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`}
            </p>
          </div>
          <div className="flex items-center gap-6">
            {dif !== null && (
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-500">{dif}%</div>
                <div className="text-xs text-gray-400">diferencia 2° vs 3°</div>
              </div>
            )}
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{fmtPct(actasActuales)}</div>
              <div className="text-xs text-gray-400">actas contadas</div>
            </div>
          </div>
        </div>

        {/* Selector de rango */}
        <div className="flex gap-1 mt-3">
          {RANGOS.map(r => (
            <button
              key={r.id}
              onClick={() => setRango(r.id)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                rango === r.id
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        {/* Posiciones actuales */}
        {lider && (
          <div className="flex gap-2 mt-3 flex-wrap">
            {/* Líder — atenuado */}
            <div className="flex items-center gap-1.5 bg-gray-50 rounded-lg px-3 py-1.5 opacity-50 text-xs">
              <span className="font-bold text-gray-400">#1</span>
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: lider.color }} />
              <span className="text-gray-600">{abrev(lider.partido)}</span>
              <span className="font-bold text-gray-500 ml-1">{fmtPct(lider.pct)}</span>
              <span className="text-gray-300 italic text-xs ml-1">fuera de carrera</span>
            </div>
            {/* Contendientes */}
            {enCarreraVivo.map((c, i) => (
              <div
                key={c.partido}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 border-2 text-xs"
                style={{ borderColor: c.color, backgroundColor: c.color + '15' }}
              >
                <span className="font-bold text-gray-500">#{i + 2}</span>
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c.color }} />
                <span className="text-gray-700 font-medium">{abrev(c.partido)}</span>
                <span className="font-bold ml-1 text-sm" style={{ color: c.color }}>{fmtPct(c.pct)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Gráfico */}
      <div className="flex-1 p-6" style={{ minHeight: 320 }}>
        {soloUnPunto ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="text-4xl mb-3">⏳</div>
            <p className="text-gray-600 font-medium">Esperando la próxima actualización de ONPE</p>
            <p className="text-gray-400 text-sm mt-1 max-w-md">
              El gráfico aparecerá cuando ONPE publique nuevos resultados
              (el sistema revisa cada 5 minutos).
            </p>
            <div className="mt-8 w-full max-w-md">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-3 font-medium">Posición actual</p>
              {enCarrera.map((c, i) => (
                <div key={c.partido} className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="flex items-center gap-1.5">
                      <span className="font-bold text-gray-400">#{i + 2}</span>
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
                      <span className="text-gray-700">{abrev(c.partido)}</span>
                    </span>
                    <span className="font-bold" style={{ color: c.color }}>{fmtPct(c.pct)}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${lider ? (c.pct / (lider.pct || 1)) * 100 : 0}%`,
                        backgroundColor: c.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                axisLine={false}
                tickLine={false}
                label={{
                  value: spanMultiDia ? 'Fecha y hora de actualización ONPE' : 'Hora de actualización ONPE',
                  position: 'insideBottom',
                  offset: -25,
                  fontSize: 11,
                  fill: '#9ca3af',
                }}
              />
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={v => `${v}%`}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                axisLine={false}
                tickLine={false}
                width={48}
              />
              <Tooltip content={<TooltipPersonalizado />} />
              <Legend
                formatter={val => <span style={{ fontSize: 12 }}>{abrev(val)}</span>}
                wrapperStyle={{ paddingTop: 8 }}
              />
              {enCarrera.map((c, i) => (
                <Line
                  key={c.partido}
                  type="monotone"
                  dataKey={c.partido}
                  name={c.partido}
                  stroke={c.color}
                  strokeWidth={i === 0 ? 3 : 2}
                  dot={{ r: 4, fill: c.color, strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
