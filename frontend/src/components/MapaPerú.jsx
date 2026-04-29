import { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { normName } from '../utils';

// Componente para ajustar bounds cuando el GeoJSON carga
function FitBounds({ geoJsonRef }) {
  const map = useMap();
  useEffect(() => {
    if (geoJsonRef.current) {
      const bounds = geoJsonRef.current.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    }
  }, [geoJsonRef.current]);
  return null;
}

export default function MapaPeru({ mapaData, tipoEleccion, onClickDep, depSeleccionado }) {
  const [geoData, setGeoData] = useState(null);
  const geoJsonRef = useRef(null);

  // Cargar GeoJSON del Perú
  useEffect(() => {
    fetch('/peru-departamentos.geojson')
      .then(r => r.json())
      .then(setGeoData)
      .catch(console.error);
  }, []);

  const esPresidencial = tipoEleccion === 'presidencial';

  // Función para obtener el color de un departamento
  function getColor(feature) {
    const nombre = feature.properties.NOMBDEP || '';
    const key = normName(nombre);

    if (!mapaData || !key) return '#9ca3af';

    const depData = mapaData[key];
    if (!depData) return '#9ca3af';

    if (esPresidencial) {
      const pct = depData.actasContabilizadas;
      if (pct == null) return '#e5e7eb';  // sin datos de ONPE
      // Gradiente continuo: 0% → azul muy claro, 100% → azul muy oscuro
      const t = Math.min(Math.max(pct / 100, 0), 1);
      const lightness = Math.round(90 - t * 68);
      return `hsl(220, 75%, ${lightness}%)`;
    }

    return depData.lider?.color || '#9ca3af';
  }

  // Función para el estilo de cada departamento
  function style(feature) {
    const nombre = feature.properties.NOMBDEP || '';
    const key = normName(nombre);
    const isSelected = key === depSeleccionado || nombre === depSeleccionado;

    return {
      fillColor: getColor(feature),
      weight: isSelected ? 3 : 1,
      opacity: 1,
      color: isSelected ? '#fbbf24' : '#ffffff',
      fillOpacity: isSelected ? 0.95 : 0.82,
      dashArray: isSelected ? null : null,
    };
  }

  // Evento hover y click en cada feature
  function onEachFeature(feature, layer) {
    const nombre = feature.properties.NOMBDEP || '';
    const key = normName(nombre);
    const depData = mapaData?.[key];

    // Tooltip
    let tooltipContent = `<strong>${nombre}</strong>`;
    if (depData) {
      if (esPresidencial) {
        tooltipContent += depData.actasContabilizadas != null
          ? `<br/>Actas: ${depData.actasContabilizadas.toFixed(1)}%`
          : `<br/><em style="color:#9ca3af">Sin datos de ONPE</em>`;
      } else {
        const lider = depData.lider;
        if (lider) {
          tooltipContent += `<br/><span style="color:${lider.color}">●</span> ${lider.partido}`;
          if (lider.pct) tooltipContent += `<br/>${lider.pct?.toFixed(2)}%`;
        }
        tooltipContent += `<br/>Actas: ${depData.actasContabilizadas?.toFixed(1)}%`;
      }
    }

    layer.bindTooltip(tooltipContent, {
      sticky: true,
      className: 'bg-white text-xs px-2 py-1 rounded shadow-md border border-gray-200',
    });

    layer.on({
      mouseover(e) {
        const l = e.target;
        l.setStyle({
          weight: 2,
          color: '#f59e0b',
          fillOpacity: 1,
        });
        l.bringToFront();
      },
      mouseout(e) {
        const l = e.target;
        const isSelected = key === depSeleccionado;
        l.setStyle({
          weight: isSelected ? 3 : 1,
          color: isSelected ? '#fbbf24' : '#ffffff',
          fillOpacity: isSelected ? 0.95 : 0.82,
        });
      },
      click() {
        onClickDep(key, nombre);
      },
    });
  }

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <MapContainer
        center={[-9.19, -75.015]}
        zoom={5}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%', position: 'absolute', inset: 0 }}
        zoomControl={true}
      >
        {/* Sin tile layer para look limpio */}
        {geoData && (
          <GeoJSON
            key={tipoEleccion + JSON.stringify(depSeleccionado)}
            ref={geoJsonRef}
            data={geoData}
            style={style}
            onEachFeature={onEachFeature}
          />
        )}
        {geoData && <FitBounds geoJsonRef={geoJsonRef} />}
      </MapContainer>

      {/* Leyenda */}
      <div style={{ position: 'absolute', bottom: 24, left: 16, zIndex: 1000 }} className="bg-white bg-opacity-95 rounded-lg shadow-lg p-3 text-xs">
        {esPresidencial ? (
          <>
            <p className="font-bold text-gray-700 mb-1.5">Avance de conteo</p>
            <div
              className="w-28 h-3 rounded mb-1"
              style={{ background: 'linear-gradient(to right, hsl(220,75%,90%), hsl(220,75%,22%))' }}
            />
            <div className="flex justify-between text-gray-500 mb-2">
              <span>0%</span>
              <span>100%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-3 rounded border border-gray-200" style={{ backgroundColor: '#e5e7eb' }} />
              <span className="text-gray-400 italic">Sin datos</span>
            </div>
          </>
        ) : (
          <>
            <p className="font-bold text-gray-700 mb-1.5">Partido líder</p>
            <p className="text-gray-400 italic">
              Clic en un<br />departamento<br />para ver detalle
            </p>
          </>
        )}
      </div>
    </div>
  );
}
