import React, { useState } from 'react'
import { planTrip } from './api'
import DailyLogSheet from './components/DailyLogSheet'
import RouteMap from './components/RouteMap'
import TripForm from './components/TripForm'
import TripSummary from './components/TripSummary'

export default function App() {
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [tripData, setTripData] = useState(null)

  async function handleSubmit(payload) {
    setLoading(true)
    setError(null)
    try {
      const data = await planTrip(payload)
      setTripData(data)
    } catch (err) {
      const status = err.response?.status
      const body   = err.response?.data

      let msg
      if (status === 502) {
        msg = 'Map service temporarily unavailable — please try again in a moment.'
      } else if (status === 400) {
        // Surface field-level validation messages from DRF
        const errors = body?.errors
        if (errors && typeof errors === 'object') {
          msg = Object.entries(errors)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join(' | ')
        } else {
          msg = body?.error || 'Invalid request — please check your inputs.'
        }
      } else {
        msg = body?.error || err.message || 'An unexpected error occurred.'
      }

      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header no-print">
        <h1>Spotter ELD — Trip Planner</h1>
      </header>

      <main className="app-main">
        {/* ── Left column: form ── */}
        <aside className="col-form no-print">
          <div className="panel">
            <h2 className="panel-title">Plan a Trip</h2>
            <TripForm onSubmit={handleSubmit} loading={loading} />
            {error && <div className="error-banner">{error}</div>}
          </div>
        </aside>

        {/* ── Right column: results ── */}
        <section className="col-results">
          {tripData ? (
            <>
              {/* Map & Summary — hidden when printing */}
              <div className="no-print">
                <RouteMap tripData={tripData} />
                <div className="panel" style={{ marginTop: '1rem' }}>
                  <h2 className="panel-title">Trip Summary</h2>
                  <TripSummary tripData={tripData} />
                </div>
              </div>

              {/* Daily Logs */}
              <div className="panel logs-panel" style={{ marginTop: '1rem' }}>
                <div className="logs-header">
                  <h2 className="panel-title" style={{ marginBottom: 0 }}>
                    Daily Logs
                    <span className="logs-count">
                      {tripData.daily_logs.length} day{tripData.daily_logs.length !== 1 ? 's' : ''}
                    </span>
                  </h2>
                  <button
                    className="btn-print no-print"
                    onClick={() => window.print()}
                    title="Print all log sheets"
                  >
                    Print All Logs
                  </button>
                </div>

                {tripData.daily_logs.map((log) => (
                  <div key={log.date} className="log-page">
                    <div className="log-date-label no-print">{log.date}</div>
                    <DailyLogSheet dailyLog={log} />
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>
                Fill in the trip details and click <strong>Plan Trip</strong> to
                see the route, HOS stops, and daily logs.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
