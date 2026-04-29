import { useState, useCallback } from 'react';
import Header from './components/Header';
import MapaPeru from './components/MapaPerú';
import PanelDetalle from './components/PanelDetalle';
import ResumenNacional from './components/ResumenNacional';
import SeccionCarrera from './components/SeccionCarrera';
import SeccionJEE from './components/SeccionJEE';
import SeccionComposicionJEE from './components/SeccionComposicionJEE';
import SeccionComparacion from './components/SeccionComparacion';
import SeccionActasDashboard from './components/SeccionActasDashboard';
import SeccionConsultaActas from './components/SeccionConsultaActas';
import { useEleccionData } from './hooks/useEleccionData';
import { TIPOS_ELECCION } from './utils';

export default function App() {
  const [tipoActivo, setTipoActivo] = useState('presidencial');
  const [depSeleccionado, setDepSeleccionado] = useState(null);
  const [depNombre, setDepNombre] = useState(null);

  const esCarrera      = tipoActivo === 'carrera';
  const esJEE          = tipoActivo === 'jee';
  const esComposicion  = tipoActivo === 'composicion-jee';
  const esComparacion  = tipoActivo === 'comparacion';
  const esActasDash    = tipoActivo === 'actas-dashboard';
  const esConsultaActas = tipoActivo === 'consulta-actas';

  // Solo fetching cuando no estamos en secciones especiales
  const { data, loading, error, refreshing, lastUpdate, refresh } = useEleccionData(
    (esCarrera || esJEE || esComposicion || esComparacion || esActasDash || esConsultaActas) ? null : tipoActivo
  );

  const handleManualRefresh = useCallback(async () => {
    // Pide al backend que descargue datos frescos de ONPE, luego refresca la UI
    try {
      await fetch('/api/refresh', { method: 'POST' });
    } catch (_) {}
    refresh();
  }, [refresh]);

  const handleCambiaTipo = useCallback((nuevoTipo) => {
    setTipoActivo(nuevoTipo);
    setDepSeleccionado(null);
    setDepNombre(null);
  }, []);

  const handleClickDep = useCallback((key, nombre) => {
    setDepSeleccionado(prev => prev === key ? null : key);
    setDepNombre(nombre);
  }, []);

  const tipoInfo = TIPOS_ELECCION.find(t => t.id === tipoActivo);

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Header con selector de elección */}
      <Header tipoActivo={tipoActivo} onCambia={handleCambiaTipo} />

      {/* Barra de resumen nacional — no aplica en secciones especiales */}
      {!esCarrera && !esJEE && !esComposicion && !esComparacion && !esActasDash && !esConsultaActas && data && !loading && (
        <ResumenNacional data={data} tipo={tipoActivo} />
      )}

      {/* Descripción */}
      <div className="bg-white border-b border-gray-200 px-4 py-1.5 flex items-center gap-3">
        <span className="text-xs text-gray-500">{tipoInfo?.desc}</span>
        {!esCarrera && !esJEE && !esComposicion && !esComparacion && !esActasDash && !esConsultaActas && (
          <div className="ml-auto flex items-center gap-2 flex-shrink-0">
            {refreshing ? (
              <span className="flex items-center gap-1 text-xs text-blue-500">
                <span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                Actualizando…
              </span>
            ) : lastUpdate ? (
              <span className="text-xs text-gray-400">
                {lastUpdate.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}
              </span>
            ) : null}
            <button
              onClick={handleManualRefresh}
              disabled={refreshing || loading}
              title="Actualizar datos de ONPE"
              className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Actualizar
            </button>
          </div>
        )}
        {!esCarrera && !esJEE && !esComposicion && !esComparacion && !esActasDash && !esConsultaActas && depNombre && (
          <>
            <span className="text-gray-300">·</span>
            <button
              onClick={() => { setDepSeleccionado(null); setDepNombre(null); }}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span className="font-semibold">{depNombre}</span>
              <span className="text-gray-400 ml-1">✕</span>
            </button>
          </>
        )}
      </div>

      {/* Sección Carrera */}
      {esCarrera && (
        <div className="flex flex-1 min-h-0">
          <SeccionCarrera />
        </div>
      )}

      {/* Sección Análisis JEE */}
      {esJEE && (
        <div className="flex flex-1 min-h-0">
          <SeccionJEE />
        </div>
      )}

      {/* Sección Composición JEE */}
      {esComposicion && (
        <div className="flex flex-1 min-h-0">
          <SeccionComposicionJEE />
        </div>
      )}

      {/* Sección Comparación de escenarios */}
      {esComparacion && (
        <div className="flex flex-1 min-h-0">
          <SeccionComparacion />
        </div>
      )}

      {/* Sección Actas Dashboard */}
      {esActasDash && (
        <div className="flex flex-1 min-h-0">
          <SeccionActasDashboard />
        </div>
      )}

      {/* Sección Consulta de Actas */}
      {esConsultaActas && (
        <SeccionConsultaActas />
      )}

      {/* Contenido principal: mapa + panel */}
      {!esCarrera && !esJEE && !esComposicion && !esComparacion && !esActasDash && !esConsultaActas && (
        <div className="flex flex-1 min-h-0">
          {/* Mapa */}
          <div className="flex-1 relative">
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-80 z-10">
                <div className="text-center">
                  <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Cargando datos de ONPE…</p>
                </div>
              </div>
            )}
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-red-50 z-10">
                <div className="text-center text-red-600 p-6">
                  <p className="font-bold text-lg">Error cargando datos</p>
                  <p className="text-sm mt-1">{error}</p>
                </div>
              </div>
            )}
            <MapaPeru
              mapaData={data?.mapa}
              tipoEleccion={tipoActivo}
              onClickDep={handleClickDep}
              depSeleccionado={depSeleccionado}
            />
          </div>

          {/* Panel lateral */}
          {data && !loading && (
            <PanelDetalle
              departamento={depSeleccionado}
              data={data}
              tipo={tipoActivo}
            />
          )}
        </div>
      )}
    </div>
  );
}
