import {
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { fmtNum, fmtPct } from '../utils';

const NOMBRES_CORTOS = {
  'FUERZA POPULAR':              'Fuerza Popular',
  'RENOVACIÓN POPULAR':          'Renovación Popular',
  'PARTIDO DEL BUEN GOBIERNO':   'Buen Gobierno',
  'JUNTOS POR EL PERÚ':          'Juntos por el Perú',
  'PARTIDO CÍVICO OBRAS':        'Cívico Obras',
  'PARTIDO PAÍS PARA TODOS':     'País para Todos',
  'AHORA NACIÓN - AN':           'Ahora Nación',
  'ALIANZA PARA EL PROGRESO':    'Alianza Progreso',
  'PODEMOS PERU':                'Podemos Perú',
  'PERU LIBRE':                  'Perú Libre',
  'ACCION POPULAR':              'Acción Popular',
};

function shortName(partido) {
  const upper = partido.toUpperCase();
  for (const [key, val] of Object.entries(NOMBRES_CORTOS)) {
    if (upper.includes(key) || key.includes(upper)) return val;
  }
  // Truncar si es muy largo
  const words = partido.split(' ');
  return words.length > 3 ? words.slice(0, 3).join(' ') + '…' : partido;
}

function TooltipPersonalizado({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-bold text-gray-800 mb-1">{d.partido}</p>
      <p style={{ color: d.color }} className="font-bold text-base">{fmtPct(d.pct)}</p>
      <p className="text-gray-500">{fmtNum(d.votos)} votos válidos</p>
      <p className="text-gray-400">Posición #{d.pos}</p>
    </div>
  );
}

export default function GraficaCarrera({ data }) {
  if (!data?.nacional?.top) return null;

  const candidatos = data.nacional.top.slice(0, 7).map((c, i) => ({
    ...c,
    pos: i + 1,
    nombre: shortName(c.partido),
  }));

  // Publicado por ONPE = contabilizadas + en JEE (ambos estados incluidos en el total publicado)
  const actas = (data.nacional.totales?.actasContabilizadas || 0) + (data.nacional.totales?.actasEnviadasJee || 0);

  // Diferencia entre 2do y 3ro, 3ro y 4to, etc.
  const dif23 = candidatos[1] && candidatos[2]
    ? (candidatos[1].pct - candidatos[2].pct).toFixed(2)
    : null;

  return (
    <div className="bg-white border-t border-gray-200 px-4 pt-3 pb-2">
      {/* Cabecera */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-bold text-gray-800">Carrera por el 2° puesto</h3>
          {dif23 !== null && (
            <span className="text-xs bg-amber-50 border border-amber-200 text-amber-700 px-2 py-0.5 rounded-full font-medium">
              2° y 3° separados por {dif23}%
            </span>
          )}
        </div>
        <span className="text-xs text-gray-400">{fmtPct(actas)} actas contabilizadas</span>
      </div>

      {/* Gráfico */}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart
          data={candidatos}
          layout="vertical"
          margin={{ top: 0, right: 60, left: 0, bottom: 0 }}
          barCategoryGap="20%"
        >
          <XAxis
            type="number"
            domain={[0, Math.ceil(candidatos[0]?.pct || 20)]}
            tickFormatter={v => `${v}%`}
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="nombre"
            width={130}
            tick={{ fontSize: 11, fill: '#374151' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<TooltipPersonalizado />} cursor={{ fill: '#f3f4f6' }} />

          {/* Línea de referencia en el % del 2do puesto */}
          {candidatos[1] && (
            <ReferenceLine
              x={candidatos[1].pct}
              stroke="#f59e0b"
              strokeDasharray="4 3"
              strokeWidth={1.5}
            />
          )}

          <Bar dataKey="pct" radius={[0, 4, 4, 0]} label={{
            position: 'right',
            formatter: v => `${v.toFixed(2)}%`,
            fontSize: 11,
            fill: '#6b7280',
          }}>
            {candidatos.map((c, i) => (
              <Cell
                key={c.partido}
                fill={c.color}
                opacity={i === 0 ? 0.4 : 1}   // 1er puesto más tenue para enfocar en la carrera
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Podio resumido debajo */}
      <div className="flex gap-4 mt-1 pt-2 border-t border-gray-100">
        {candidatos.slice(1, 5).map((c) => (
          <div key={c.partido} className="flex items-center gap-1.5 flex-1 min-w-0">
            <span className="text-xs font-bold text-gray-400">#{c.pos}</span>
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: c.color }}
            />
            <span className="text-xs text-gray-600 truncate">{c.nombre}</span>
            <span className="text-xs font-bold ml-auto" style={{ color: c.color }}>
              {fmtPct(c.pct)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
