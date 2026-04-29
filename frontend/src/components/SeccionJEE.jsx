import { useEffect, useState } from 'react';
import { fmtNum, fmtPct } from '../utils';

const POLL_INTERVAL = 5 * 60 * 1000;

function BaraEstados({ contab, jee, pend, sinProc }) {
  const total = contab + jee + pend + sinProc;
  if (!total) return null;
  const pContab = (contab / total) * 100;
  const pJee    = (jee    / total) * 100;
  const pPend   = (pend   / total) * 100;
  const pSin    = (sinProc/ total) * 100;
  return (
    <div className="flex h-4 rounded-full overflow-hidden w-full">
      {pContab > 0 && <div style={{ width: `${pContab}%`, backgroundColor: '#22c55e' }} title={`Contabilizadas ${pContab.toFixed(1)}%`} />}
      {pJee    > 0 && <div style={{ width: `${pJee}%`,    backgroundColor: '#3b82f6' }} title={`Enviadas JEE ${pJee.toFixed(1)}%`} />}
      {pPend   > 0 && <div style={{ width: `${pPend}%`,   backgroundColor: '#f59e0b' }} title={`Pendientes JEE ${pPend.toFixed(1)}%`} />}
      {pSin    > 0 && <div style={{ width: `${pSin}%`,    backgroundColor: '#e5e7eb' }} title={`Sin procesar ${pSin.toFixed(1)}%`} />}
    </div>
  );
}

function Leyenda() {
  return (
    <div className="flex flex-wrap gap-4 text-xs text-gray-600">
      {[
        { color: '#22c55e', label: 'Contabilizadas', desc: 'ONPE escrutó y publicó' },
        { color: '#3b82f6', label: 'Enviadas al JEE', desc: 'Certificadas por el JEE' },
        { color: '#f59e0b', label: 'Pendientes JEE', desc: 'Aún NO en el conteo' },
        { color: '#e5e7eb', label: 'Sin procesar', desc: 'No iniciadas', border: true },
      ].map(({ color, label, desc, border }) => (
        <div key={label} className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm flex-shrink-0"
            style={{ backgroundColor: color, border: border ? '1px solid #d1d5db' : 'none' }}
          />
          <span className="font-medium">{label}</span>
          <span className="text-gray-400">— {desc}</span>
        </div>
      ))}
    </div>
  );
}

export default function SeccionJEE() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  async function fetchData() {
    try {
      const r = await fetch('/api/analisis-jee');
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
  const proc = nacional.contabilizadas.n + nacional.enviadas_jee.n;
  const pctProc = nacional.contabilizadas.pct + nacional.enviadas_jee.pct;

  return (
    <div className="flex-1 overflow-auto bg-gray-50 p-4 space-y-4">

      {/* Cabecera */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Análisis de Actas — Flujo ONPE → JEE</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {lastUpdate && `Actualizado ${lastUpdate.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`}
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-gray-900">{pctProc.toFixed(2)}%</div>
            <div className="text-xs text-gray-400">del total procesado</div>
          </div>
        </div>

        {/* Barra nacional */}
        <BaraEstados
          contab={nacional.contabilizadas.n}
          jee={nacional.enviadas_jee.n}
          pend={nacional.pendientes_jee.n}
          sinProc={nacional.sin_procesar.n}
        />
        <div className="mt-3">
          <Leyenda />
        </div>

        {/* Tarjetas de resumen */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
          {[
            {
              label: 'Contabilizadas',
              n: nacional.contabilizadas.n,
              pct: nacional.contabilizadas.pct,
              color: 'text-green-600',
              bg: 'bg-green-50',
            },
            {
              label: 'Enviadas al JEE',
              n: nacional.enviadas_jee.n,
              pct: nacional.enviadas_jee.pct,
              color: 'text-blue-600',
              bg: 'bg-blue-50',
            },
            {
              label: 'Pendientes JEE',
              n: nacional.pendientes_jee.n,
              pct: nacional.pendientes_jee.pct,
              color: 'text-amber-600',
              bg: 'bg-amber-50',
            },
            {
              label: 'Total actas',
              n: nacional.total_actas,
              pct: 100,
              color: 'text-gray-700',
              bg: 'bg-gray-50',
            },
          ].map(({ label, n, pct, color, bg }) => (
            <div key={label} className={`${bg} rounded-lg p-3`}>
              <div className={`text-xl font-bold ${color}`}>{fmtNum(n)}</div>
              <div className={`text-sm font-semibold ${color}`}>{pct.toFixed(2)}%</div>
              <div className="text-xs text-gray-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>

        {/* Votos y estimaciones */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-lg font-bold text-gray-800">{fmtNum(nacional.total_validos_publicados)}</div>
            <div className="text-xs text-gray-500">Votos válidos publicados</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-lg font-bold text-gray-800">{fmtNum(nacional.votos_por_acta_promedio)}</div>
            <div className="text-xs text-gray-500">Votos válidos / acta (promedio)</div>
          </div>
          <div className="bg-amber-50 rounded-lg p-3">
            <div className="text-lg font-bold text-amber-700">~{fmtNum(nacional.votos_estimados_pendientes)}</div>
            <div className="text-xs text-gray-500">Votos estimados aún pendientes</div>
          </div>
        </div>
      </div>

      {/* Tabla por departamento */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100">
          <h3 className="font-bold text-gray-800 text-sm">Por departamento — ordenado por mayor incertidumbre</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Departamentos con más actas pendientes (que aún podrían mover resultados) aparecen primero
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-2">Departamento</th>
                <th className="text-right px-3 py-2">Total</th>
                <th className="text-right px-3 py-2 text-green-700">Contab.</th>
                <th className="text-right px-3 py-2 text-blue-700">JEE</th>
                <th className="text-right px-3 py-2 text-amber-700">Pend.</th>
                <th className="px-4 py-2">Estado</th>
                <th className="text-right px-3 py-2">Votos estim. pendientes</th>
                <th className="text-left px-4 py-2">Lider actual</th>
                <th className="text-right px-3 py-2">Margen 1°-2°</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {departamentos.map((dep) => (
                <tr key={dep.nombre} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 font-medium text-gray-800 whitespace-nowrap">{dep.nombre}</td>
                  <td className="px-3 py-2.5 text-right text-gray-500">{fmtNum(dep.total_actas)}</td>
                  <td className="px-3 py-2.5 text-right">
                    <span className="text-green-700 font-medium">{dep.contabilizadas.pct.toFixed(1)}%</span>
                    <span className="text-gray-400 ml-1">({fmtNum(dep.contabilizadas.n)})</span>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <span className="text-blue-600 font-medium">{dep.enviadas_jee.pct.toFixed(1)}%</span>
                    <span className="text-gray-400 ml-1">({fmtNum(dep.enviadas_jee.n)})</span>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <span className={`font-bold ${dep.pendientes_jee.n > 0 ? 'text-amber-600' : 'text-gray-300'}`}>
                      {dep.pendientes_jee.pct.toFixed(1)}%
                    </span>
                    <span className="text-gray-400 ml-1">({fmtNum(dep.pendientes_jee.n)})</span>
                  </td>
                  <td className="px-4 py-2.5 min-w-32">
                    <BaraEstados
                      contab={dep.contabilizadas.n}
                      jee={dep.enviadas_jee.n}
                      pend={dep.pendientes_jee.n}
                      sinProc={dep.sin_procesar.n}
                    />
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {dep.votos_estimados_pendientes > 0 ? (
                      <span className="text-amber-600 font-medium">~{fmtNum(dep.votos_estimados_pendientes)}</span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {dep.top3[0] && (
                      <div className="flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: dep.top3[0].color }}
                        />
                        <span className="text-gray-700 truncate max-w-28">{dep.top3[0].partido.split(' ').slice(0, 3).join(' ')}</span>
                        <span className="font-bold" style={{ color: dep.top3[0].color }}>
                          {dep.top3[0].pct.toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {dep.margen_1_vs_2 != null ? (
                      <span className={`font-bold ${dep.margen_1_vs_2 < 3 ? 'text-red-500' : dep.margen_1_vs_2 < 8 ? 'text-amber-500' : 'text-gray-600'}`}>
                        {dep.margen_1_vs_2.toFixed(2)}%
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Nota explicativa */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-xs text-blue-800">
        <p className="font-bold mb-1">¿Qué es el flujo ONPE → JEE?</p>
        <p>
          Cada acta pasa por tres etapas: (1) <strong>Contabilización ONPE</strong> — el resultado se ingresa al sistema y se publica en tiempo real;
          (2) <strong>Envío al JEE</strong> — el acta es remitida al Jurado Electoral Especial del distrito para su revisión y certificación oficial;
          (3) <strong>Pendientes</strong> — actas ya contabilizadas que aún están en tránsito hacia el JEE.
          Las actas pendientes representan votos que <strong>aún no son oficiales</strong> y en teoría podrían ser observadas.
        </p>
      </div>
    </div>
  );
}
