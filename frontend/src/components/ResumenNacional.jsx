import { fmtNum, fmtPct } from '../utils';

export default function ResumenNacional({ data, tipo }) {
  if (!data?.nacional) return null;
  const { top, totales } = data.nacional;

  return (
    <div className="bg-blue-900 text-white px-4 py-2 flex items-center gap-6 overflow-x-auto text-sm">
      {/* Avance general — tres estados ONPE distintos */}
      {totales && (
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="flex flex-col items-center">
            <div
              className="text-lg font-bold leading-tight"
              style={{ color: (totales.actasContabilizadas ?? 0) >= 50 ? '#4ade80' : '#fbbf24' }}
            >
              {fmtPct(totales.actasContabilizadas)}
            </div>
            <div className="text-xs text-blue-300 leading-tight">contabilizadas</div>
          </div>
          {totales.actasEnviadasJee > 0 && (
            <>
              <div className="text-blue-600 text-sm">+</div>
              <div className="flex flex-col items-center">
                <div className="text-base font-bold text-purple-300 leading-tight">
                  {fmtPct(totales.actasEnviadasJee)}
                </div>
                <div className="text-xs text-blue-300 leading-tight">en JEE</div>
              </div>
            </>
          )}
          <div className="text-xs text-blue-400 self-end mb-0.5">
            / {fmtNum(totales.totalActas)} actas
          </div>
        </div>
      )}

      <div className="w-px h-8 bg-blue-700 flex-shrink-0" />

      {/* Top candidatos */}
      {top && top.slice(0, 5).map((c, i) => (
        <div key={i} className="flex items-center gap-2 flex-shrink-0">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: c.color }}
          />
          <div>
            <div className="font-semibold text-xs leading-tight">
              {c.partido.length > 22 ? c.partido.substring(0, 22) + '…' : c.partido}
            </div>
            {c.candidato && tipo === 'presidencial' && (
              <div className="text-blue-300 text-xs leading-tight">
                {c.candidato.split(' ').slice(0, 2).join(' ')}
              </div>
            )}
          </div>
          <div className="font-bold text-sm text-yellow-300">
            {fmtPct(c.pct)}
          </div>
        </div>
      ))}
    </div>
  );
}
