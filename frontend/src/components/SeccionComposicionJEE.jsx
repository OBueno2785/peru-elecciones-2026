import { useEffect, useState } from 'react';
import { fmtNum, fmtPct } from '../utils';

const POLL_INTERVAL = 5 * 60 * 1000;
const EXCLUIR_LABELS = ['VOTOS NULOS', 'VOTOS EN BLANCO', 'VOTOS IMPUGNADOS'];

function BaraVotos({ candidatos, height = 'h-5' }) {
  const total = candidatos.reduce((s, c) => s + c.pct, 0);
  if (!total) return null;
  return (
    <div className={`flex ${height} rounded overflow-hidden w-full`}>
      {candidatos.slice(0, 8).map((c) => (
        <div
          key={c.partido}
          style={{ width: `${c.pct}%`, backgroundColor: c.color }}
          title={`${c.partido}: ${c.pct.toFixed(2)}%`}
        />
      ))}
      {total < 99 && (
        <div style={{ width: `${100 - total}%`, backgroundColor: '#e5e7eb' }} />
      )}
    </div>
  );
}

function DesvBadge({ desv }) {
  if (desv == null) return null;
  const abs = Math.abs(desv);
  if (abs < 0.5) return <span className="text-gray-300 text-xs">≈nac</span>;
  const color = desv > 0 ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50';
  return (
    <span className={`text-xs font-bold px-1 rounded ${color}`}>
      {desv > 0 ? '+' : ''}{desv.toFixed(1)}%
    </span>
  );
}

function TablaDesvNacional({ departamentos, topPartidos }) {
  // Muestra para cada depto la desviación vs nacional del top-5 partidos
  const partidos5 = topPartidos.slice(0, 5);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 text-gray-500 uppercase tracking-wide">
          <tr>
            <th className="text-left px-3 py-2 sticky left-0 bg-gray-50">Departamento</th>
            {partidos5.map(p => (
              <th key={p.partido} className="px-3 py-2 text-right min-w-28">
                <div className="flex items-center justify-end gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                  <span className="truncate max-w-24">{p.partido.split(' ').slice(0, 3).join(' ')}</span>
                </div>
                <div className="text-gray-400 font-normal">(nac: {p.pct.toFixed(1)}%)</div>
              </th>
            ))}
            <th className="text-right px-3 py-2">Pend. actas</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {departamentos.map(dep => {
            const mapCands = Object.fromEntries(dep.candidatos.map(c => [c.partido, c]));
            return (
              <tr key={dep.nombre} className="hover:bg-gray-50">
                <td className="px-3 py-2 font-medium text-gray-800 sticky left-0 bg-white whitespace-nowrap">
                  {dep.nombre}
                </td>
                {partidos5.map(p => {
                  const c = mapCands[p.partido];
                  return (
                    <td key={p.partido} className="px-3 py-2 text-right">
                      {c ? (
                        <div>
                          <span className="font-bold" style={{ color: p.color }}>{c.pct.toFixed(1)}%</span>
                          <span className="ml-1"><DesvBadge desv={c.desv_nac} /></span>
                        </div>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                  );
                })}
                <td className="px-3 py-2 text-right">
                  {dep.n_pendientes > 0 ? (
                    <div>
                      <span className="text-amber-600 font-bold">{dep.n_pendientes}</span>
                      <span className="text-gray-400 ml-1">actas</span>
                    </div>
                  ) : <span className="text-green-500 text-xs">completo</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function SeccionComposicionJEE() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [vista, setVista]     = useState('barras');   // 'barras' | 'desviacion'
  const [lastUpdate, setLastUpdate] = useState(null);

  async function fetchData() {
    try {
      const r = await fetch('/api/composicion-jee');
      setData(await r.json());
      setLastUpdate(new Date());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, POLL_INTERVAL);
    return () => clearInterval(t);
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!data) return null;

  const { nacional, departamentos } = data;
  const topPartidos = nacional.top;

  return (
    <div className="flex-1 overflow-auto bg-gray-50 p-4 space-y-4">

      {/* Cabecera */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Composición del voto — Actas certificadas por JEE</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Votos válidos por partido en cada departamento · fuente: ONPE estadoActa=JEE
              {lastUpdate && ` · ${lastUpdate.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">{fmtNum(nacional.total_validos)}</div>
            <div className="text-xs text-gray-400">votos válidos certificados</div>
          </div>
        </div>

        {/* Barra nacional */}
        <BaraVotos candidatos={topPartidos} height="h-6" />
        <div className="flex flex-wrap gap-3 mt-3">
          {topPartidos.slice(0, 7).map(p => (
            <div key={p.partido} className="flex items-center gap-1.5 text-xs">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: p.color }} />
              <span className="text-gray-700 font-medium">{p.partido.split(' ').slice(0, 3).join(' ')}</span>
              <span className="font-bold" style={{ color: p.color }}>{p.pct.toFixed(2)}%</span>
              <span className="text-gray-400">({fmtNum(p.votos)})</span>
            </div>
          ))}
        </div>
      </div>

      {/* Controles de vista */}
      <div className="flex gap-2">
        {[
          { id: 'barras',     label: 'Composición por departamento' },
          { id: 'desviacion', label: 'Desviación vs. media nacional' },
        ].map(v => (
          <button
            key={v.id}
            onClick={() => setVista(v.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              vista === v.id
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Vista: barras apiladas por departamento */}
      {vista === 'barras' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="font-bold text-gray-800 text-sm">Composición de votos por departamento</h3>
            <p className="text-xs text-gray-400 mt-0.5">Ordenado por peso electoral (mayor número de votos primero)</p>
          </div>
          <div className="divide-y divide-gray-50">
            {departamentos.map(dep => (
              <div key={dep.nombre} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-3 mb-1.5">
                  <span className="text-xs font-bold text-gray-700 w-32 flex-shrink-0">{dep.nombre}</span>
                  <div className="flex-1">
                    <BaraVotos candidatos={dep.candidatos} height="h-4" />
                  </div>
                  <div className="text-xs text-gray-400 w-24 text-right flex-shrink-0">
                    {fmtNum(dep.total_validos)} votos
                  </div>
                </div>
                {/* Lider + 2do + pendientes */}
                <div className="flex items-center gap-3 pl-[8.5rem] text-xs">
                  {dep.candidatos.slice(0, 3).map((c, i) => (
                    <span key={c.partido} className="flex items-center gap-1">
                      <span className="text-gray-400">#{i + 1}</span>
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
                      <span className="text-gray-600">{c.partido.split(' ').slice(0, 3).join(' ')}</span>
                      <span className="font-bold" style={{ color: c.color }}>{c.pct.toFixed(1)}%</span>
                    </span>
                  ))}
                  {dep.n_pendientes > 0 && (
                    <span className="ml-auto text-amber-600 font-medium">
                      ⚠ {dep.n_pendientes} actas pendientes (~{fmtNum(dep.votos_estimados_pendientes)} votos)
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Vista: desviación vs nacional */}
      {vista === 'desviacion' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="font-bold text-gray-800 text-sm">Desviación respecto a la media nacional</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Verde = el partido supera su media nacional en ese departamento · Rojo = por debajo
            </p>
          </div>
          <TablaDesvNacional departamentos={departamentos} topPartidos={topPartidos} />
        </div>
      )}

      {/* Nota */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-xs text-blue-800">
        <p className="font-bold mb-1">Fuente y metodología</p>
        <p>
          Los votos aquí mostrados provienen del endpoint <code className="bg-blue-100 px-1 rounded">estadoActa=JEE</code> de
          ONPE, que devuelve la composición de todos los votos cuyas actas han completado el proceso de
          certificación ante el Jurado Electoral Especial. Incluye tanto las actas <em>contabilizadas</em> como
          las <em>enviadas al JEE</em>. Las actas <em>pendientes</em> (~3.7% nacional) aún no están en este conteo.
        </p>
      </div>
    </div>
  );
}
