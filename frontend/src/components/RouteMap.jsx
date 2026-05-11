import L from 'leaflet'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'
import React, { useEffect } from 'react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'

// Fix Leaflet's broken default icon URLs when bundled with Vite/Webpack
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl })

function FitBounds({ positions }) {
  const map = useMap()
  useEffect(() => {
    if (positions.length > 0) {
      map.fitBounds(positions, { padding: [40, 40] })
    }
  }, [positions, map])
  return null
}

export default function RouteMap({ tripData }) {
  const { geometry, waypoints } = tripData.route

  // GeoJSON geometry is [lon, lat]; Leaflet requires [lat, lon]
  const positions = geometry.map(([lon, lat]) => [lat, lon])
  const center    = positions[0] ?? [39.5, -98.35]

  return (
    <div className="map-container">
      <MapContainer
        center={center}
        zoom={5}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <Polyline positions={positions} color="#1e3a8a" weight={4} opacity={0.85} />

        {waypoints.map((wp) => (
          <Marker key={wp.label} position={[wp.lat, wp.lon]}>
            <Popup>
              <strong>{wp.label}</strong>
              <br />
              <span style={{ fontSize: '0.82rem', color: '#555' }}>{wp.display_name}</span>
            </Popup>
          </Marker>
        ))}

        <FitBounds positions={positions} />
      </MapContainer>
    </div>
  )
}
