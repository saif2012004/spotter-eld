import React from 'react'

const STOP_META = {
  fuel:        { label: 'Fuel Stop',    cls: 'badge-fuel'  },
  rest_30min:  { label: '30-min Break', cls: 'badge-30min' },
  rest_10hr:   { label: '10-hr Reset',  cls: 'badge-10hr'  },
  restart_34hr:{ label: '34-hr Restart',cls: 'badge-34hr'  },
}

export default function TripSummary({ tripData }) {
  const { summary, route, stops } = tripData

  const stats = [
    { label: 'Total Miles',     value: route.total_miles.toFixed(1) },
    { label: 'Driving Hours',   value: summary.total_driving_hours.toFixed(1) },
    { label: 'Total Trip Hours',value: summary.total_trip_hours.toFixed(1)  },
    { label: 'Calendar Days',   value: summary.days },
    { label: 'Cycle Hrs After', value: summary.cycle_hours_used_after.toFixed(1), accent: true },
  ]

  return (
    <>
      <div className="summary-stats">
        {stats.map((s) => (
          <div key={s.label} className={`stat-card${s.accent ? ' accent' : ''}`}>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {stops.length > 0 ? (
        <table className="stops-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>At Mile</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {stops.map((stop, i) => {
              const meta = STOP_META[stop.type] ?? { label: stop.type, cls: '' }
              return (
                <tr key={i}>
                  <td>
                    <span className={`stop-badge ${meta.cls}`}>{meta.label}</span>
                  </td>
                  <td>{stop.at_mile.toLocaleString()}</td>
                  <td>{stop.duration_hours === 0.25 ? '15 min' : `${stop.duration_hours} hr`}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>No mandatory stops required.</p>
      )}
    </>
  )
}
