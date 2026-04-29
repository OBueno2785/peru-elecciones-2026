import { useEffect, useState } from 'react';
import { fmtNum, fmtPct } from '../utils';

const POLL_INTERVAL = 5 * 60 * 1000;

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

function PanelVotos({ data, headerColor, isEstimation }) {
  if (!data) return null;
  const { label, descripcion, actas_pct, actas_n, total_votos, top } = data;
  const maxPct = top?.[0]?.pct ?? 1;

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm flex flex-col overflow-hidden h-full">
      <div className={`px-4 py-3 text-white ${headerColor}`}>
        <div className="flex items-center justify-between gap-2">
          <span className="font-bold text-sm">{label}</span>
          {isEstimation && (
            <span className="text-xs bg-white bg-opacity-20 rounded px-2 py-0.5 flex-shrink-0">estimación</span>
          )}
        </div>
        <p className="text-xs opacity-80 mt-0.5 leading-tight">{descripcion}</p>
      </div>

      <div className="flex divide-x divide-gray-100 border-b border-gray-100">
        <div className="flex-1 px-3 py-2 text-center">
          <div className="text-base font-bold text-gray-800">{fmtPct(actas_pct)}</div>
          <div className="text-xs text-gray-400">actas</div>
        </div>
        <div className="flex-1 px-3 py-2 text-center">
          <div className="text-base font-bold text-gray-800">{fmtNum(actas_n)}</div>
          <div className="text-xs text-gray-400">n° actas</div>
        </div>
        <div className="flex-1 px-3 py-2 text-center">
          <div className="text-base font-bold text-gray-800">{fmtNum(total_votos)}</div>
          <div className="text-xs text-gray-400">votos válidos</div>
        </div>
      </div>

      <div className="flex-1 px-4 py-3 space-y-2.5">
        {top?.length > 0 ? top.map((c, i) => (
          <div key={c.partido}>
            <div className="flex items-center justify-between text-xs mb-0.5">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="font-bold text-gray-400 w-4 flex-shrink-0">#{i + 1}</span>
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: c.color }} />
                <span className="text-gray-700 truncate">{abrev(c.partido)}</span>
              </div>
              <span className="font-bold ml-2 flex-shrink-0 tabular-nums" style={{ color: c.color }}>
                {c.pct.toFixed(2)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${(c.pct / maxPct) * 100}%`, backgroundColor: c.color }}
              />
            </div>
          </div>
        )) : (
          <p className="text-xs text-gray-400 text-center py-4">Sin datos</p>
        )}
      </div>
    </div>
  );
}

function ActasFlowBar({ totales }) {
  if (!totales) return null;
  const { pct_contab, pct_jee, pct_pend } = totales;
  const pct_sin = Math.max(0, 100 - pct_contab - pct_jee - pct_pend);
  const segments = [
    { label: 'Contabilizadas', pct: pct_contab, color: '#2563EB' },
    { label: 'En JEE',         pct: pct_jee,    color: '#7C3AED' },
    { label: 'Pendientes',     pct: pct_pend,   color: '#F59E0B' },
    { label: 'Sin procesar',   pct: pct_sin,    color: '#E5E7EB' },
  ].filter(s => s.pct > 0);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-5 py-4">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
        <div>
          <h3 className="font-bold text-gray-800 text-sm">Estado de las actas electorales</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Total: {fmtNum(totales.total_actas)} actas · {fmtNum(totales.votos_publicados)} votos publicados
          </p>
        </div>
        <div className="flex gap-3 flex-wrap">
          {segments.map(s => (
            <div key={s.label} className="flex items-center gap-1.5 text-xs">
              <span className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: s.color }} />
              <span className="text-gray-600">{s.label}</span>
              <span className="font-bold text-gray-800">{s.pct.toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex h-4 rounded-lg overflow-hidden">
        {segments.map(s => (
          <div
            key={s.label}
            style={{ width: `${s.pct}%`, backgroundColor: s.color }}
            title={`${s.label}: ${s.pct.toFixed(2)}%`}
          />
        ))}
      </div>
    </div>
  );
}

function ZonaIncertidumbre({ incertidumbre, pendientes }) {
  if (!incertidumbre?.length) return null;
  const vPend = pendientes?.votos_estimados ?? 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="font-bold text-gray-800 text-sm">Zona de incertidumbre</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          ¿Pueden las {fmtNum(pendientes?.actas_n)} actas pendientes (~{fmtNum(vPend)} votos estimados) cambiar alguna posición?
        </p>
      </div>
      <div className="divide-y divide-gray-50">
        {incertidumbre.map(r => (
          <div key={r.partido} className="px-5 py-3 flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 w-44 flex-shrink-0">
              <span className="font-bold text-gray-400 text-sm">#{r.posicion}</span>
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: r.color }} />
              <span className="text-sm font-medium text-gray-800">{abrev(r.partido)}</span>
            </div>
            <div className="text-sm tabular-nums font-bold" style={{ color: r.color }}>
              {r.pct.toFixed(2)}%
            </div>
            <div className="flex gap-4 flex-wrap text-xs">
              <div className="text-center">
                <div className={`font-bold ${r.puede_subir ? 'text-amber-500' : 'text-gray-300'}`}>
                  ▲ {fmtNum(r.votos_al_de_arriba)} votos
                </div>
                <div className="text-gray-400">para subir un puesto</div>
              </div>
              {r.votos_sobre_el_de_abajo != null && (
                <div className="text-center">
                  <div className={`font-bold ${r.puede_bajar ? 'text-red-400' : 'text-gray-300'}`}>
                    ▼ {fmtNum(r.votos_sobre_el_de_abajo)} votos
                  </div>
                  <div className="text-gray-400">margen sobre el de abajo</div>
                </div>
              )}
              {r.puede_subir && (
                <span className="px-2 py-0.5 bg-amber-50 text-amber-700 font-bold rounded text-xs self-center">
                  ¡Puede subir!
                </span>
              )}
              {r.puede_bajar && (
                <span className="px-2 py-0.5 bg-red-50 text-red-600 font-bold rounded text-xs self-center">
                  En riesgo
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SeccionComparacion() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const r = await fetch('/api/comparacion-actas');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        if (!mounted) return;
        setData(d);
        setLastUpdate(new Date());
      } catch (e) {
        if (mounted) setError(e.message);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchData();
    const t = setInterval(fetchData, POLL_INTERVAL);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-red-500 text-sm px-8 text-center">
        {error ? `Error: ${error}` : 'Sin datos'}
      </div>
    );
  }

  const { sin_jee, con_jee, proyeccion, pendientes, incertidumbre, totales } = data;
  const pendDepTop = pendientes?.por_departamento?.slice(0, 15) ?? [];
  const maxPend = pendDepTop[0]?.pendientes_n ?? 1;

  return (
    <div className="flex-1 overflow-auto bg-gray-50 p-4 space-y-4">

      {/* Cabecera */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-5 py-3 flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Comparación de escenarios de conteo</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Cómo varía el resultado según las actas incluidas
            {lastUpdate && ` · ${lastUpdate.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`}
          </p>
        </div>
      </div>

      {/* Barra de estado de actas */}
      <ActasFlowBar totales={totales} />

      {/* Tres paneles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PanelVotos data={sin_jee}    headerColor="bg-slate-600"  isEstimation={sin_jee?.es_estimacion} />
        <PanelVotos data={con_jee}    headerColor="bg-blue-600"   isEstimation={con_jee?.es_estimacion} />
        <PanelVotos data={proyeccion} headerColor="bg-emerald-600" isEstimation={proyeccion?.es_estimacion} />
      </div>

      {/* Zona de incertidumbre */}
      <ZonaIncertidumbre incertidumbre={incertidumbre} pendientes={pendientes} />

      {/* Actas pendientes por departamento */}
      {pendDepTop.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="font-bold text-gray-800 text-sm">Actas pendientes por departamento</h3>
              <p className="text-xs text-gray-400 mt-0.5">Composición desconocida — aún no escrutadas</p>
            </div>
            <div className="flex gap-4 text-center">
              <div>
                <div className="text-lg font-bold text-amber-500">{fmtNum(pendientes?.actas_n)}</div>
                <div className="text-xs text-gray-400">actas</div>
              </div>
              <div>
                <div className="text-lg font-bold text-amber-500">{fmtPct(pendientes?.actas_pct)}</div>
                <div className="text-xs text-gray-400">del total</div>
              </div>
              <div>
                <div className="text-lg font-bold text-gray-700">~{fmtNum(pendientes?.votos_estimados)}</div>
                <div className="text-xs text-gray-400">votos estimados</div>
              </div>
            </div>
          </div>
          <div className="px-5 py-4 space-y-2.5">
            {pendDepTop.map(dep => (
              <div key={dep.nombre}>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-700 font-medium w-32 flex-shrink-0">{dep.nombre}</span>
                  <div className="flex-1">
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-amber-400 rounded-full"
                        style={{ width: `${(dep.pendientes_n / maxPend) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-amber-600 font-bold w-20 text-right">{fmtNum(dep.pendientes_n)} actas</span>
                  <span className="text-gray-400 w-24 text-right">~{fmtNum(dep.votos_estimados)} votos</span>
                  <div className="flex gap-1 w-40 flex-shrink-0">
                    {dep.top2?.slice(0, 2).map((c, i) => (
                      <span key={c.partido} className="flex items-center gap-0.5">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
                        <span style={{ color: c.color }} className="font-bold">{c.pct.toFixed(1)}%</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nota metodológica */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-xs text-blue-800 space-y-1">
        <p className="font-bold">Metodología y limitaciones</p>
        <p>
          <strong>Solo contabilizadas (estimado):</strong> ONPE no expone composición separada por estado de acta — los endpoints <code>estadoActa=CONTABILIZADA</code> y <code>estadoActa=JEE</code> devuelven los mismos datos. Se estima escalando los votos totales por el ratio de actas contabilizadas ({fmtPct(totales?.pct_contab)}). Los porcentajes son idénticos al Panel 2; solo difiere el total de votos (~{fmtNum((totales?.pct_contab ?? 0) / ((totales?.pct_contab ?? 0) + (totales?.pct_jee ?? 0.001)) * 100 | 0)}% del total publicado).
          · <strong>Publicado por ONPE:</strong> datos oficiales ONPE — suma de contabilizadas ({fmtPct(totales?.pct_contab)}) + en JEE ({fmtPct(totales?.pct_jee)}) = {fmtPct((totales?.pct_contab ?? 0) + (totales?.pct_jee ?? 0))} de actas.
          · <strong>Proyección 100%:</strong> los {fmtNum(pendientes?.actas_n)} votos pendientes se distribuyen según el perfil de voto de cada departamento con actas por contar (proyección geográfica ponderada).
          · <strong>Zona de incertidumbre:</strong> muestra si los ~{fmtNum(pendientes?.votos_estimados)} votos estimados son suficientes para cambiar alguna posición.
        </p>
      </div>
    </div>
  );
}
