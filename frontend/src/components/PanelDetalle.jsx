import { fmtNum, fmtPct, progressColor } from '../utils';

function BarraCandidato({ cand, maxPct, rank }) {
  const pct = cand.pct || 0;
  const barWidth = maxPct > 0 ? (pct / maxPct) * 100 : 0;

  return (
    <div className="mb-2.5">
      <div className="flex items-center justify-between mb-0.5">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: cand.color || '#888' }}
          />
          <span className="text-xs font-medium text-gray-800 truncate">
            {rank}. {cand.partido}
          </span>
        </div>
        <span className="text-xs font-bold text-gray-700 ml-2 tabular-nums">
          {fmtPct(pct)}
        </span>
      </div>
      {cand.candidato && (
        <p className="text-xs text-gray-500 ml-5 mb-0.5 truncate">{cand.candidato}</p>
      )}
      <div className="ml-5 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${barWidth}%`,
            backgroundColor: cand.color || '#888',
          }}
        />
      </div>
      <p className="text-xs text-gray-400 ml-5 mt-0.5">
        {fmtNum(cand.votos)} votos válidos
      </p>
    </div>
  );
}

export default function PanelDetalle({ departamento, data, tipo }) {
  if (!data) return null;

  const esPresidencial = tipo === 'presidencial';
  const mapa = data.mapa || {};
  const nacional = data.nacional;

  // Buscar datos del departamento seleccionado
  const depKey = departamento
    ? Object.keys(mapa).find(k =>
        k === departamento || k.includes(departamento) || departamento.includes(k)
      )
    : null;

  const depData = depKey ? mapa[depKey] : null;

  // Para presidencial: usar resultados del departamento si existen (ahora disponibles)
  // Para senado/diputados: usar datos del departamento si existen
  const candidatos = esPresidencial
    ? (depData?.top?.length ? depData.top : (nacional ? nacional.top : []))
    : (depData ? depData.top : (nacional ? nacional.top : []));

  // Actas: usar siempre el dato del departamento si está disponible
  const actasPct = depData?.actasContabilizadas ?? (nacional?.totales?.actasContabilizadas ?? null);
  const actasPctDep = depData?.actasContabilizadas ?? null;  // específico del dep
  const actasPctNac = nacional?.totales?.actasContabilizadas ?? null;  // nacional

  const totalActas = depData ? depData.totalActas : (nacional?.totales?.totalActas || 0);
  const contabilizadas = depData ? depData.contabilizadas : (nacional?.totales?.contabilizadas || 0);
  const nombreMostrado = depData ? depData.nombre : (departamento ? departamento : 'Nacional');

  const maxPct = candidatos.length > 0 ? (candidatos[0]?.pct || 1) : 1;

  const tituloPanel = departamento ? nombreMostrado : 'Resultados Nacionales';

  return (
    <aside className="w-80 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
      {/* Cabecera del panel */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
        <h2 className="font-bold text-gray-900 text-sm">{tituloPanel}</h2>

        {/* Avance de conteo del departamento — presidencial */}
        {esPresidencial && departamento && (
          <div className="mt-2">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span className="font-medium">Actas contadas en {nombreMostrado}</span>
              <span className="font-bold" style={{ color: actasPctDep != null ? progressColor(actasPctDep) : '#9ca3af' }}>
                {actasPctDep != null ? fmtPct(actasPctDep) : 'Sin datos'}
              </span>
            </div>
            <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(actasPctDep ?? 0, 100)}%`,
                  backgroundColor: actasPctDep != null ? progressColor(actasPctDep) : '#e5e7eb',
                }}
              />
            </div>
            {actasPctNac != null && (
              <div className="flex items-center gap-1.5 mt-1.5">
                <div className="flex-1 h-px bg-gray-200" />
                <span className="text-xs text-gray-400">Nacional: {fmtPct(actasPctNac)}</span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
            )}
          </div>
        )}

        {/* Avance para vista sin departamento o para senado/diputados */}
        {(!esPresidencial || !departamento) && (
          <div className="mt-2">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Actas contabilizadas</span>
              <span className="font-bold" style={{ color: actasPct != null ? progressColor(actasPct) : '#9ca3af' }}>
                {actasPct != null ? fmtPct(actasPct) : 'Sin datos'}
              </span>
            </div>
            {actasPct != null ? (
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all"
                  style={{ width: `${Math.min(actasPct, 100)}%`, backgroundColor: progressColor(actasPct) }} />
              </div>
            ) : (
              <div className="h-2 bg-gray-100 rounded-full" />
            )}
            <p className="text-xs text-gray-400 mt-0.5">
              {actasPct != null
                ? `${fmtNum(contabilizadas)} de ${fmtNum(totalActas)} actas`
                : 'ONPE aún no reporta totales para este distrito'}
            </p>
          </div>
        )}
      </div>

      {/* Lista de candidatos */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {candidatos.length === 0 ? (
          <p className="text-sm text-gray-400 text-center mt-8">Sin datos disponibles</p>
        ) : (
          <>
            <p className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wide">
              {esPresidencial
                ? (depData?.top?.length && departamento
                    ? `Resultados en ${nombreMostrado}`
                    : 'Resultados nacionales')
                : 'Organizaciones Políticas'}
              {' '}· Top {Math.min(candidatos.length, 10)}
            </p>
            {candidatos.slice(0, 10).map((c, i) => (
              <BarraCandidato key={i} cand={c} maxPct={maxPct} rank={i + 1} />
            ))}
          </>
        )}
      </div>

      {/* Pie */}
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-2">
        <p className="text-xs text-gray-400 text-center">
          Fuente: ONPE · Datos al{' '}
          {new Date().toLocaleDateString('es-PE', {
            day: '2-digit', month: 'long', hour: '2-digit', minute: '2-digit',
          })}
        </p>
      </div>
    </aside>
  );
}
