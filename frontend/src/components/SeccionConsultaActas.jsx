import { useState, useCallback, useRef } from 'react';
import { fmtNum, fmtPct } from '../utils';

const ESTADOS = {
  C: { label: 'Contabilizada', color: 'text-green-600 bg-green-50' },
  E: { label: 'Enviada JEE',   color: 'text-blue-600 bg-blue-50'  },
  O: { label: 'Observada',     color: 'text-red-600 bg-red-50'    },
  P: { label: 'Pendiente',     color: 'text-yellow-600 bg-yellow-50' },
  T: { label: 'Digitalizada',  color: 'text-purple-600 bg-purple-50' },
  D: { label: 'Digitada',      color: 'text-gray-600 bg-gray-50'  },
};

const PARTY_COLORS = [
  '#E63946','#1D3557','#457B9D','#F97316','#2A9D8F',
  '#E9C46A','#264653','#E76F51','#9B5DE5','#43AA8B',
  '#90BE6D','#577590','#F9C74F','#F8961E','#43A6C6',
];

function Badge({ code }) {
  const e = ESTADOS[code] || { label: code || '?', color: 'text-gray-500 bg-gray-100' };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${e.color}`}>
      {e.label}
    </span>
  );
}

function ActaDetail({ acta, imgUrl, imgLoading, imgError }) {
  const partidos = (acta.detalle || [])
    .filter(d => d.grafico === 1 && d.nvotos > 0)
    .sort((a, b) => b.nvotos - a.nvotos);
  const blancos = (acta.detalle || []).find(d => d.descripcion === 'VOTOS EN BLANCO')?.nvotos ?? 0;
  const nulos   = (acta.detalle || []).find(d => d.descripcion === 'VOTOS NULOS')?.nvotos ?? 0;
  const maxVotos = partidos[0]?.nvotos || 1;
  const sumPartidos = partidos.reduce((s, p) => s + p.nvotos, 0);
  const validos = acta.totalVotosValidos || 0;
  const coincide = Math.abs(sumPartidos - validos) <= 2;

  return (
    <div className="flex flex-col gap-4">
      {/* Cabecera */}
      <div className="bg-blue-900 text-white rounded-lg px-4 py-3">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-lg font-bold">Mesa {acta.codigoMesa}</span>
          <Badge code={acta.codigoEstadoActa} />
          <span className="text-blue-200 text-sm">{acta.nombreLocalVotacion}</span>
        </div>
        <div className="text-blue-200 text-xs mt-1">
          {acta.ubigeoNivel01} › {acta.ubigeoNivel02} › {acta.ubigeoNivel03}
          {acta.descripcionSolucionTecnologica && (
            <span className="ml-3 text-blue-300">· {acta.descripcionSolucionTecnologica}</span>
          )}
        </div>
      </div>

      {/* Imagen + datos en columnas */}
      <div className="flex gap-4 min-h-0">

        {/* Columna izquierda: imagen del PDF */}
        <div className="w-1/2 flex flex-col">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Acta física (PDF escaneado)
          </div>
          <div className="border border-gray-200 rounded-lg overflow-auto bg-gray-50 flex-1 min-h-64 flex items-center justify-center">
            {imgLoading && (
              <div className="text-center p-6">
                <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-gray-500">Renderizando PDF…</p>
              </div>
            )}
            {imgError && (
              <div className="text-center p-6 text-gray-400">
                <svg className="w-12 h-12 mx-auto mb-2 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-xs">PDF no disponible localmente</p>
                <p className="text-xs mt-1 text-gray-300">(solo se descargaron PDFs de actas observadas/pendientes)</p>
              </div>
            )}
            {imgUrl && !imgLoading && !imgError && (
              <img src={imgUrl} alt={`Acta mesa ${acta.codigoMesa}`} className="w-full h-auto" />
            )}
          </div>
        </div>

        {/* Columna derecha: datos digitados */}
        <div className="w-1/2 flex flex-col gap-3">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Datos registrados en el sistema
          </div>

          {/* Totales */}
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-200 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">Electores hábiles</span>
              <b>{fmtNum(acta.totalElectoresHabiles)}</b>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Votos emitidos</span>
              <b>{fmtNum(acta.totalVotosEmitidos)}</b>
            </div>
            <div className="flex justify-between text-green-700">
              <span>Votos válidos</span>
              <b>{fmtNum(validos)}</b>
            </div>
            <div className="flex justify-between text-gray-400 text-xs">
              <span>Blancos / Nulos</span>
              <span>{fmtNum(blancos)} / {fmtNum(nulos)}</span>
            </div>
            {/* Barra de participación */}
            <div className="pt-1">
              <div className="flex justify-between text-xs text-gray-500 mb-0.5">
                <span>Participación</span>
                <span>{acta.porcentajeParticipacionCiudadana?.toFixed(2)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-blue-500"
                  style={{ width: `${Math.min(acta.porcentajeParticipacionCiudadana || 0, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Resultados por partido */}
          <div className="flex-1 overflow-y-auto border border-gray-200 rounded-lg">
            <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Resultados por partido
            </div>
            <div className="divide-y divide-gray-50">
              {partidos.map((p, i) => (
                <div key={p.ccodigo} className="px-3 py-1.5">
                  <div className="flex justify-between items-center gap-2">
                    <span className="text-xs text-gray-700 flex-1 min-w-0 truncate" title={p.descripcion}>
                      {p.candidato?.[0]
                        ? `${p.candidato[0].apellidoPaterno} ${p.candidato[0].apellidoMaterno}, ${p.candidato[0].nombres}`
                        : p.descripcion}
                    </span>
                    <span className="text-xs font-bold text-gray-800 flex-shrink-0">{fmtNum(p.nvotos)}</span>
                    <span className="text-xs text-gray-400 w-12 text-right flex-shrink-0">
                      {p.nporcentajeVotosValidos?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-0.5 w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full"
                      style={{
                        width: `${(p.nvotos / maxVotos) * 100}%`,
                        backgroundColor: PARTY_COLORS[i % PARTY_COLORS.length],
                      }}
                    />
                  </div>
                  <div className="text-xs text-gray-400 truncate">{p.descripcion}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Verificación */}
          <div className={`text-xs px-3 py-2 rounded-lg ${coincide ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {coincide ? '✓' : '✗'} Suma partidos: <b>{fmtNum(sumPartidos)}</b> vs votos válidos: <b>{fmtNum(validos)}</b>
            {!coincide && <span className="ml-2 font-bold">INCONSISTENCIA</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SeccionConsultaActas() {
  const [filters, setFilters] = useState({ dept: '', mesa: '', dist: '', estado: '' });
  const [results, setResults]  = useState(null);
  const [total, setTotal]      = useState(0);
  const [page, setPage]        = useState(0);
  const [loading, setLoading]  = useState(false);

  const [selected, setSelected]    = useState(null);  // item from results
  const [actaData, setActaData]    = useState(null);
  const [actaLoading, setActaLoading] = useState(false);
  const [imgUrl, setImgUrl]        = useState(null);
  const [imgLoading, setImgLoading]= useState(false);
  const [imgError, setImgError]    = useState(false);

  const PAGE_SIZE = 30;

  const search = useCallback(async (p = 0) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        dept: filters.dept, mesa: filters.mesa,
        dist: filters.dist, estado: filters.estado,
        page: p, size: PAGE_SIZE,
      });
      const r = await fetch(`/api/actas/search?${params}`);
      const d = await r.json();
      setResults(d.items);
      setTotal(d.total);
      setPage(p);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const selectActa = useCallback(async (item) => {
    setSelected(item);
    setActaData(null);
    setImgUrl(null);
    setImgError(false);

    setActaLoading(true);
    try {
      const r = await fetch(`/api/actas/${item.id}/data`);
      const d = await r.json();
      setActaData(d);
    } finally {
      setActaLoading(false);
    }

    if (item.tiene_pdf) {
      setImgLoading(true);
      setImgError(false);
      const url = `/api/actas/${item.id}/image`;
      const probe = await fetch(url);
      if (probe.ok) {
        setImgUrl(url + '?t=' + Date.now());
      } else {
        setImgError(true);
      }
      setImgLoading(false);
    } else {
      setImgError(true);
    }
  }, []);

  const handleKey = (e) => { if (e.key === 'Enter') search(0); };

  return (
    <div className="flex flex-1 min-h-0 bg-gray-50">

      {/* Panel izquierdo: búsqueda + lista */}
      <div className="w-80 flex flex-col border-r border-gray-200 bg-white">

        {/* Filtros */}
        <div className="p-3 border-b border-gray-100 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Consulta de Actas</p>
          <input
            className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
            placeholder="Departamento (ej. AMAZONAS)"
            value={filters.dept}
            onChange={e => setFilters(f => ({ ...f, dept: e.target.value }))}
            onKeyDown={handleKey}
          />
          <input
            className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
            placeholder="Distrito (ej. BAGUA)"
            value={filters.dist}
            onChange={e => setFilters(f => ({ ...f, dist: e.target.value }))}
            onKeyDown={handleKey}
          />
          <input
            className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
            placeholder="Mesa (ej. 000228)"
            value={filters.mesa}
            onChange={e => setFilters(f => ({ ...f, mesa: e.target.value }))}
            onKeyDown={handleKey}
          />
          <select
            className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
            value={filters.estado}
            onChange={e => setFilters(f => ({ ...f, estado: e.target.value }))}
          >
            <option value="">Todos los estados</option>
            <option value="C">Contabilizada</option>
            <option value="E">Enviada JEE</option>
            <option value="O">Observada</option>
            <option value="P">Pendiente</option>
          </select>
          <button
            onClick={() => search(0)}
            disabled={loading}
            className="w-full bg-blue-700 text-white py-1.5 rounded text-sm font-medium hover:bg-blue-800 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Buscando…' : 'Buscar'}
          </button>
        </div>

        {/* Resultados */}
        <div className="flex-1 overflow-y-auto">
          {results === null && (
            <p className="text-xs text-gray-400 text-center mt-8 px-4">
              Ingresa un filtro y presiona Buscar para consultar actas
            </p>
          )}
          {results !== null && (
            <>
              <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100">
                {fmtNum(total)} actas encontradas
                {total > PAGE_SIZE && ` · página ${page + 1} de ${Math.ceil(total / PAGE_SIZE)}`}
              </div>
              {results.map(item => (
                <button
                  key={item.id}
                  onClick={() => selectActa(item)}
                  className={`w-full text-left px-3 py-2 border-b border-gray-50 hover:bg-blue-50 transition-colors ${selected?.id === item.id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-gray-800">Mesa {item.mesa}</span>
                    <Badge code={item.codigo_estado} />
                    {item.tiene_pdf && (
                      <span className="text-xs text-purple-500" title="PDF disponible">PDF</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 truncate mt-0.5">{item.local || item.dist}</div>
                  <div className="text-xs text-gray-400">{item.dist} · {fmtNum(item.validos)} votos</div>
                </button>
              ))}

              {/* Paginación */}
              {total > PAGE_SIZE && (
                <div className="flex justify-between px-3 py-2">
                  <button
                    onClick={() => search(page - 1)}
                    disabled={page === 0 || loading}
                    className="text-xs text-blue-600 disabled:opacity-30"
                  >
                    ← Anterior
                  </button>
                  <button
                    onClick={() => search(page + 1)}
                    disabled={(page + 1) * PAGE_SIZE >= total || loading}
                    className="text-xs text-blue-600 disabled:opacity-30"
                  >
                    Siguiente →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Panel derecho: detalle */}
      <div className="flex-1 overflow-y-auto p-4">
        {!selected && (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Selecciona un acta de la lista para ver el detalle
          </div>
        )}
        {selected && actaLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {selected && actaData && !actaLoading && (
          <ActaDetail
            acta={actaData}
            imgUrl={imgUrl}
            imgLoading={imgLoading}
            imgError={imgError}
          />
        )}
      </div>
    </div>
  );
}
