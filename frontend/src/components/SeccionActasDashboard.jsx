import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { fmtNum, fmtPct } from '../utils';

const COLORES_ESTADO = {
  'Contabilizada': '#22c55e',
  'Enviada JEE':   '#3b82f6',
  'Pendiente':     '#f59e0b',
  'Observada':     '#ef4444',
  'Digitalizada':  '#8b5cf6',
  'Digitada':      '#06b6d4',
  'Desconocido':   '#9ca3af',
};

const PARTY_COLORS = [
  '#E63946','#1D3557','#457B9D','#F97316','#2A9D8F',
  '#E9C46A','#264653','#E76F51','#9B5DE5','#43AA8B',
  '#90BE6D','#577590','#F9C74F','#F8961E','#43A6C6',
];

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-2xl font-bold text-gray-800">{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3 mt-6 border-b border-gray-200 pb-1">
      {children}
    </h2>
  );
}

export default function SeccionActasDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/actas-dashboard')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-600">Cargando análisis de actas…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-red-600 p-6">
          <p className="font-bold text-lg">Error cargando datos</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-xs mt-2 text-gray-500">Asegúrate de haber ejecutado eda_actas.py</p>
        </div>
      </div>
    );
  }

  const g = data.resumen_general;
  const ev = data.estadisticas_votos;
  const c = data.consistencia;
  const al = data.alertas_participacion;

  // Pie de estados
  const estadoData = Object.entries(g.por_estado).map(([name, value]) => ({ name, value }));

  // Top partidos para bar chart
  const topPartidos = data.top_15_partidos.map((p, i) => ({
    partido: p.partido.length > 28 ? p.partido.slice(0, 28) + '…' : p.partido,
    votos: p.votos,
    pct: p.pct_sobre_validos,
    color: PARTY_COLORS[i % PARTY_COLORS.length],
  }));

  // Departamentos para tabla
  const depts = data.por_departamento;

  const participacion = ev.participacion_pct;

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">

        {/* Tarjetas resumen */}
        <SectionTitle>Resumen General</SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard
            label="Total actas"
            value={fmtNum(g.total_actas_analizadas)}
          />
          <StatCard
            label="Contabilizadas"
            value={fmtPct(g.pct_contabilizadas)}
            sub={fmtNum(g.por_estado['Contabilizada']) + ' actas'}
          />
          <StatCard
            label="Votos válidos"
            value={fmtNum(ev.total_votos_validos_global)}
          />
          <StatCard
            label="Participación media"
            value={participacion?.mean != null ? participacion.mean.toFixed(1) + '%' : '–'}
            sub={`Mediana ${participacion?.median?.toFixed(1)}%`}
          />
        </div>

        {/* Pie de estados + alertas */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-2">

          {/* Pie */}
          <div className="bg-white rounded-lg shadow p-4">
            <SectionTitle>Distribución por Estado</SectionTitle>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={estadoData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
                  labelLine={false}
                >
                  {estadoData.map((entry) => (
                    <Cell key={entry.name} fill={COLORES_ESTADO[entry.name] || '#9ca3af'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => fmtNum(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Estadísticas por mesa */}
          <div className="bg-white rounded-lg shadow p-4">
            <SectionTitle>Estadísticas por Mesa de Votación</SectionTitle>
            <div className="space-y-3 text-sm">
              {[
                { label: 'Electores hábiles', key: 'electores_habiles' },
                { label: 'Votos emitidos', key: 'votos_emitidos' },
                { label: 'Votos válidos', key: 'votos_validos' },
                { label: 'Participación (%)', key: 'participacion_pct' },
              ].map(({ label, key }) => {
                const s = ev[key];
                if (!s) return null;
                return (
                  <div key={key} className="border-b border-gray-100 pb-2">
                    <span className="font-medium text-gray-700">{label}</span>
                    <div className="grid grid-cols-3 gap-2 mt-1 text-xs text-gray-500">
                      <span>Media: <b className="text-gray-700">{s.mean?.toFixed(1)}</b></span>
                      <span>Mediana: <b className="text-gray-700">{s.median?.toFixed(1)}</b></span>
                      <span>Stdev: <b className="text-gray-700">{s.stdev?.toFixed(1)}</b></span>
                      <span>Min: <b className="text-gray-700">{s.min}</b></span>
                      <span>Max: <b className="text-gray-700">{s.max}</b></span>
                      <span>Total: <b className="text-gray-700">{fmtNum(s.total)}</b></span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Top 15 partidos */}
        <SectionTitle>Top 15 Partidos / Candidatos (% sobre votos válidos)</SectionTitle>
        <div className="bg-white rounded-lg shadow p-4">
          <ResponsiveContainer width="100%" height={380}>
            <BarChart
              data={topPartidos}
              layout="vertical"
              margin={{ left: 8, right: 40, top: 4, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tickFormatter={v => v.toFixed(1) + '%'} tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="partido"
                width={195}
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                formatter={(v, _, props) => [
                  `${v.toFixed(2)}% (${fmtNum(props.payload.votos)} votos)`,
                  'Porcentaje'
                ]}
              />
              <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
                {topPartidos.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Votos especiales */}
          <div className="flex gap-6 mt-3 text-sm border-t border-gray-100 pt-3">
            <span className="text-gray-500">
              En blanco: <b className="text-gray-800">{fmtNum(data.votos_especiales.en_blanco)}</b>
              <span className="text-gray-400 ml-1">
                ({fmtPct(data.votos_especiales.en_blanco / ev.total_votos_validos_global * 100)})
              </span>
            </span>
            <span className="text-gray-500">
              Nulos: <b className="text-gray-800">{fmtNum(data.votos_especiales.nulos)}</b>
            </span>
            <span className="text-gray-500">
              Impugnados: <b className="text-gray-800">{fmtNum(data.votos_especiales.impugnados)}</b>
            </span>
          </div>
        </div>

        {/* Consistencia + alertas */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-4">
            <SectionTitle>Consistencia Numérica</SectionTitle>
            <div className="flex items-center gap-4">
              <div className={`text-4xl font-bold ${c.actas_con_inconsistencias === 0 ? 'text-green-500' : 'text-red-500'}`}>
                {c.actas_con_inconsistencias === 0 ? '✓ 0' : fmtNum(c.actas_con_inconsistencias)}
              </div>
              <div className="text-sm text-gray-500">
                actas con inconsistencias
                <br />
                <span className="text-gray-400">({c.pct_inconsistencias?.toFixed(2)}% del total)</span>
              </div>
            </div>
            {Object.keys(c.tipos_frecuentes || {}).length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-gray-600">
                {Object.entries(c.tipos_frecuentes).map(([tipo, n]) => (
                  <li key={tipo} className="flex justify-between">
                    <span>{tipo}</span><span className="font-bold">{n}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <SectionTitle>Alertas de Participación</SectionTitle>
            <div className="flex gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-orange-500">{fmtNum(al.alta_participacion_gt95)}</div>
                <div className="text-xs text-gray-500 mt-1">mesas con participación<br />&gt; 95%</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-500">{fmtNum(al.baja_participacion_lt20)}</div>
                <div className="text-xs text-gray-500 mt-1">mesas con participación<br />&lt; 20%</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-700">{fmtNum(al.total_alertas)}</div>
                <div className="text-xs text-gray-500 mt-1">alertas totales</div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabla departamentos */}
        <SectionTitle>Distribución por Departamento</SectionTitle>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-2">Departamento</th>
                <th className="text-right px-4 py-2">Actas</th>
                <th className="text-right px-4 py-2">Contabilizadas</th>
                <th className="text-right px-4 py-2">% Cont.</th>
                <th className="text-right px-4 py-2">Votos válidos</th>
                <th className="px-4 py-2 w-32">Avance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {depts.map((d) => (
                <tr key={d.departamento} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-700">{d.departamento}</td>
                  <td className="px-4 py-2 text-right text-gray-600">{fmtNum(d.actas)}</td>
                  <td className="px-4 py-2 text-right text-gray-600">{fmtNum(d.actas_contabilizadas)}</td>
                  <td className="px-4 py-2 text-right">
                    <span className={`font-semibold ${d.pct_contabilizadas >= 95 ? 'text-green-600' : d.pct_contabilizadas >= 80 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {d.pct_contabilizadas.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right text-gray-700">{fmtNum(d.total_votos_validos)}</td>
                  <td className="px-4 py-2">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${Math.min(d.pct_contabilizadas, 100)}%`,
                          backgroundColor: d.pct_contabilizadas >= 95 ? '#22c55e' : d.pct_contabilizadas >= 80 ? '#f59e0b' : '#ef4444',
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Muestra de acta real vs datos digitados */}
        <SectionTitle>Muestra: Acta Física vs. Datos Registrados</SectionTitle>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-3">
            <span className="text-sm text-gray-600">
              Mesa <b>000228</b> · IEP 16192 · <b>BAGUA, AMAZONAS</b> · Estado: <span className="text-green-600 font-semibold">Contabilizada</span>
            </span>
            <span className="ml-auto text-xs text-gray-400">
              Imagen del acta descargada de ONPE · comparación con JSON digitado
            </span>
          </div>
          <img
            src="/api/acta-sample-image"
            alt="Comparación acta física vs datos ONPE — Mesa 000228 Bagua"
            className="w-full h-auto"
            style={{ imageRendering: 'auto' }}
          />
        </div>

        <div className="mt-6 text-xs text-gray-400 text-center pb-4">
          Datos de {fmtNum(g.total_actas_analizadas)} actas presidenciales descargadas desde ONPE
        </div>
      </div>
    </div>
  );
}
