import React from 'react'

// ── Layout constants (all in SVG user units) ─────────────────────────────
const W        = 1100
const PAD      = 8
const LABEL_W  = 174          // left column: row labels
const TOTAL_W  = 96           // right column: total hours
const GRID_W   = W - LABEL_W - TOTAL_W   // 830
const HOUR_W   = GRID_W / 24             // ~34.58

const HDR_H    = 190          // header section height
const TLBL_H   = 24           // time-label strip above rows
const GRID_TOP = HDR_H + TLBL_H + 4     // 218
const ROW_H    = 56
const GRID_BOT = GRID_TOP + ROW_H * 4   // 442
const TICK_SZ  = 7            // quarter-hour tick height

const REM_TOP      = GRID_BOT + 30      // 472
const REM_HDR_H    = 20
const REM_LINE_H   = 16
const MAX_REMARKS  = 9
const REM_BODY_H   = REM_LINE_H * MAX_REMARKS
const REM_BOT      = REM_TOP + REM_HDR_H + REM_BODY_H + 8

const SHIP_TOP  = REM_BOT + 12
const SHIP_H    = 76
const RECAP_TOP = SHIP_TOP + SHIP_H + 12
const RECAP_H   = 140
const SVG_H     = RECAP_TOP + RECAP_H + 12

// ── Lookup tables ────────────────────────────────────────────────────────
const STATUS_ROW = {
  off_duty:            0,
  sleeper:             1,
  driving:             2,
  on_duty_not_driving: 3,
}

const ROW_DEFS = [
  { key: 'off_duty',            label: '1. Off Duty' },
  { key: 'sleeper',             label: '2. Sleeper Berth' },
  { key: 'driving',             label: '3. Driving' },
  { key: 'on_duty_not_driving', label: '4. On Duty (Not Driving)' },
]

const HOUR_LABELS = [
  'M','1','2','3','4','5','6','7','8','9','10','11',
  'N','1','2','3','4','5','6','7','8','9','10','11','M',
]

// ── Pure helpers ─────────────────────────────────────────────────────────

/** "HH:MM" → fractional hours. end="00:00" is treated as 24 (midnight). */
function t2h(s, isEnd = false) {
  const [h, m] = s.split(':').map(Number)
  const v = h + m / 60
  return isEnd && v === 0 ? 24 : v
}

/** Fractional hours → SVG x-coordinate inside the grid. */
function hx(hours) {
  return LABEL_W + (hours / 24) * GRID_W
}

/** Row index → SVG y-coordinate of the row's centre line. */
function ry(rowIdx) {
  return GRID_TOP + rowIdx * ROW_H + ROW_H / 2
}

/** Round to nearest 0.25. */
function roundQ(v) { return Math.round(v * 4) / 4 }

/** Format hours as a string (no trailing ".00"). */
function fmtH(v) {
  const r = roundQ(v || 0)
  if (r === 0)      return '0'
  if (r % 1 === 0)  return `${r}`
  return r.toFixed(2)
}

/**
 * Build the SVG <path d> string that draws the classic step-line duty graph:
 * horizontal segment on the correct row, vertical connector to the next row.
 */
function buildDutyPath(events) {
  const segs = []
  events.forEach((ev, i) => {
    const x1  = hx(t2h(ev.start))
    const x2  = hx(t2h(ev.end, true))
    const row = STATUS_ROW[ev.status] ?? 0
    const y   = ry(row)
    if (x2 - x1 < 0.5) return          // skip zero-length events

    // Horizontal segment
    segs.push(`M${x1},${y} H${x2}`)

    // Vertical connector to next event
    if (i < events.length - 1) {
      const nextRow = STATUS_ROW[events[i + 1].status] ?? 0
      if (nextRow !== row) segs.push(`M${x2},${y} V${ry(nextRow)}`)
    }
  })
  return segs.join(' ')
}

// ── Sub-components (pure SVG fragments) ─────────────────────────────────

function HdrField({ label, value, x, y, w }) {
  return (
    <>
      <text x={x + 2} y={y} fontSize={8} fill="#64748b" fontFamily="Arial,sans-serif">
        {label.toUpperCase()}
      </text>
      <text x={x + 2} y={y + 13} fontSize={11} fill="#0f172a" fontFamily="Arial,sans-serif">
        {value || '—'}
      </text>
      <line x1={x} y1={y + 17} x2={x + w} y2={y + 17} stroke="#cbd5e1" strokeWidth={0.6} />
    </>
  )
}

function RecapCol({ x, y, title, rows }) {
  return (
    <>
      <text x={x} y={y + 13} fontSize={10} fontWeight="bold"
            fill="#1e3a8a" fontFamily="Arial,sans-serif">
        {title}
      </text>
      {rows.map(([label, value], i) => (
        <g key={i}>
          <text x={x + 4} y={y + 32 + i * 24} fontSize={9}
                fill="#475569" fontFamily="Arial,sans-serif">{label}</text>
          <text x={x + 260} y={y + 32 + i * 24} fontSize={11} fontWeight="700"
                fill="#0f172a" fontFamily="Arial,sans-serif">{value}</text>
          <line x1={x} y1={y + 36 + i * 24} x2={x + 360} y2={y + 36 + i * 24}
                stroke="#e2e8f0" strokeWidth={0.5} />
        </g>
      ))}
    </>
  )
}

// ── Main component ───────────────────────────────────────────────────────

export default function DailyLogSheet({
  dailyLog,
  carrierName    = 'Spotter ELD Demo',
  carrierAddress = '—',
  truckNumbers   = '—',
  homeTerminal   = '—',
}) {
  if (!dailyLog) return null
  const { date, events = [], totals = {}, miles_today = 0 } = dailyLog

  const onDutyH = (totals.driving || 0) + (totals.on_duty_not_driving || 0)
  const totalH  = Object.values(totals).reduce((a, b) => a + b, 0)
  const recap   = dailyLog.recap ?? {}

  const fmtR = (v) => (v !== undefined && v !== null) ? v.toFixed(1) : '—'

  // Derive From / To from first / last meaningful event location
  const meaningful = events.filter(e => e.location !== 'Rest')
  const fromLoc = meaningful[0]?.location ?? '—'
  const toLoc   = meaningful[meaningful.length - 1]?.location ?? '—'

  return (
    <svg
      viewBox={`0 0 ${W} ${SVG_H}`}
      width="100%"
      style={{ display: 'block', background: 'white' }}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* ── Outer border ── */}
      <rect x={PAD} y={PAD} width={W - PAD * 2} height={SVG_H - PAD * 2}
            fill="white" stroke="#334155" strokeWidth={1.2} />

      {/* ════════════════════════════════════════════════════════
          HEADER
          ════════════════════════════════════════════════════════ */}

      {/* Title bar */}
      <rect x={PAD} y={PAD} width={W - PAD * 2} height={36} fill="#1e3a8a" />
      <text x={(W) / 2} y={31} textAnchor="middle"
            fontSize={15} fontWeight="bold" fill="white" fontFamily="Arial,sans-serif">
        Driver&apos;s Daily Log (24 Hours)
      </text>
      <text x={W - PAD - 6} y={28} textAnchor="end"
            fontSize={8.5} fill="#93c5fd" fontFamily="Arial,sans-serif">
        Original — Retain in Vehicle for 6 Months
      </text>

      {/* Header field rows */}
      <HdrField label="Date"                    value={date}          x={PAD + 4}  y={52} w={140} />
      <HdrField label="From"                    value={fromLoc}       x={170}      y={52} w={180} />
      <HdrField label="To"                      value={toLoc}         x={380}      y={52} w={180} />
      <HdrField label="Total Miles Driving Today" value={miles_today.toFixed(1)} x={590} y={52} w={200} />
      <HdrField label="Total Mileage Today"     value={miles_today.toFixed(1)} x={820} y={52} w={160} />

      <HdrField label="Driver's Signature" value="___________________________" x={PAD + 4} y={84}  w={390} />
      <HdrField label="Co-Driver"          value="___________________________" x={440}     y={84}  w={340} />

      <HdrField label="Carrier Name"        value={carrierName}    x={PAD + 4} y={116} w={310} />
      <HdrField label="Main Office Address" value={carrierAddress} x={360}     y={116} w={430} />

      <HdrField label="Truck / Vehicle No." value={truckNumbers} x={PAD + 4} y={148} w={220} />
      <HdrField label="Trailer No."         value="—"            x={270}     y={148} w={180} />
      <HdrField label="Home Terminal"       value={homeTerminal}  x={490}     y={148} w={280} />

      {/* Header bottom border */}
      <line x1={PAD} y1={HDR_H} x2={W - PAD} y2={HDR_H} stroke="#334155" strokeWidth={1} />

      {/* ════════════════════════════════════════════════════════
          GRID AREA
          ════════════════════════════════════════════════════════ */}

      {/* "Total Hours" column header */}
      <rect x={LABEL_W + GRID_W} y={GRID_TOP - TLBL_H} width={TOTAL_W} height={TLBL_H}
            fill="#1e3a8a" />
      <text x={LABEL_W + GRID_W + TOTAL_W / 2} y={GRID_TOP - TLBL_H / 2 + 4}
            textAnchor="middle" fontSize={8.5} fontWeight="bold"
            fill="white" fontFamily="Arial,sans-serif">
        Total Hours
      </text>

      {/* Hour labels (top) */}
      {HOUR_LABELS.map((lbl, i) => {
        const isBold = (i === 0 || i === 12 || i === 24)
        return (
          <text key={i} x={hx(i)} y={GRID_TOP - 7} textAnchor="middle"
                fontSize={isBold ? 11 : 9.5}
                fontWeight={isBold ? 'bold' : 'normal'}
                fill="#1e293b" fontFamily="Arial,sans-serif">
            {lbl}
          </text>
        )
      })}

      {/* Grid rows */}
      {ROW_DEFS.map(({ key, label }, idx) => {
        const top = GRID_TOP + idx * ROW_H
        const mid = top + ROW_H / 2
        const isEven = idx % 2 === 0
        return (
          <g key={key}>
            {/* Row background */}
            <rect x={LABEL_W} y={top} width={GRID_W} height={ROW_H}
                  fill={isEven ? '#f8fafc' : '#fff'} />

            {/* Row label */}
            <text x={LABEL_W - 8} y={mid + 4} textAnchor="end"
                  fontSize={11} fill="#1e293b" fontFamily="Arial,sans-serif">
              {label}
            </text>

            {/* Row border */}
            <rect x={LABEL_W} y={top} width={GRID_W} height={ROW_H}
                  fill="none" stroke="#94a3b8" strokeWidth={0.4} />

            {/* Totals cell */}
            <rect x={LABEL_W + GRID_W} y={top} width={TOTAL_W} height={ROW_H}
                  fill={isEven ? '#eff6ff' : '#f8fafc'} stroke="#94a3b8" strokeWidth={0.4} />
            <text x={LABEL_W + GRID_W + TOTAL_W / 2} y={mid + 5}
                  textAnchor="middle" fontSize={14} fontWeight="700"
                  fill="#1e3a8a" fontFamily="Arial,sans-serif">
              {fmtH(totals[key])}
            </text>
          </g>
        )
      })}

      {/* Vertical hour lines */}
      {Array.from({ length: 25 }, (_, i) => {
        const x = hx(i)
        const isMajor = (i === 0 || i === 12 || i === 24)
        return (
          <line key={i} x1={x} y1={GRID_TOP} x2={x} y2={GRID_BOT}
                stroke={isMajor ? '#475569' : '#cbd5e1'}
                strokeWidth={isMajor ? 0.9 : 0.4} />
        )
      })}

      {/* Quarter-hour tick marks (top and bottom of grid) */}
      {Array.from({ length: 24 }, (_, h) =>
        [1, 2, 3].map(q => {
          const x = hx(h + q / 4)
          return (
            <g key={`${h}q${q}`}>
              <line x1={x} y1={GRID_TOP}           x2={x} y2={GRID_TOP + TICK_SZ}
                    stroke="#94a3b8" strokeWidth={q === 2 ? 0.5 : 0.35} />
              <line x1={x} y1={GRID_BOT - TICK_SZ} x2={x} y2={GRID_BOT}
                    stroke="#94a3b8" strokeWidth={q === 2 ? 0.5 : 0.35} />
            </g>
          )
        })
      )}

      {/* Left label area border */}
      <rect x={PAD} y={GRID_TOP} width={LABEL_W - PAD} height={ROW_H * 4}
            fill="none" stroke="#94a3b8" strokeWidth={0.5} />

      {/* ── THE DUTY STATUS LINE ── */}
      <path d={buildDutyPath(events)}
            stroke="#000" strokeWidth={2.2} fill="none" strokeLinecap="square" />

      {/* Grid outer border (on top so it's clean) */}
      <rect x={LABEL_W} y={GRID_TOP} width={GRID_W} height={ROW_H * 4}
            fill="none" stroke="#475569" strokeWidth={0.9} />

      {/* Total row below grid */}
      <text x={LABEL_W - 8} y={GRID_BOT + 20} textAnchor="end"
            fontSize={10} fill="#475569" fontFamily="Arial,sans-serif">
        Total
      </text>
      <rect x={LABEL_W + GRID_W} y={GRID_BOT} width={TOTAL_W} height={22}
            fill="#1e3a8a" />
      <text x={LABEL_W + GRID_W + TOTAL_W / 2} y={GRID_BOT + 15}
            textAnchor="middle" fontSize={12} fontWeight="bold"
            fill="white" fontFamily="Arial,sans-serif">
        {fmtH(totalH)}
      </text>

      {/* ════════════════════════════════════════════════════════
          REMARKS
          ════════════════════════════════════════════════════════ */}

      <rect x={PAD} y={REM_TOP} width={W - PAD * 2}
            height={REM_HDR_H + REM_BODY_H + 10}
            fill="none" stroke="#94a3b8" strokeWidth={0.6} />

      {/* Remarks header bar */}
      <rect x={PAD} y={REM_TOP} width={W - PAD * 2} height={REM_HDR_H}
            fill="#f1f5f9" />
      <text x={PAD + 8} y={REM_TOP + 14} fontSize={11}
            fontWeight="bold" fill="#1e3a8a" fontFamily="Arial,sans-serif">
        REMARKS
      </text>
      <text x={W - PAD - 8} y={REM_TOP + 14} textAnchor="end"
            fontSize={9} fill="#64748b" fontFamily="Arial,sans-serif">
        Include time and location of any stops, pickups, dropoffs, or fuel stops
      </text>

      {/* Remark lines */}
      {events.slice(0, MAX_REMARKS).map((ev, i) => {
        const y = REM_TOP + REM_HDR_H + 4 + i * REM_LINE_H
        const milesStr = ev.status === 'driving' && ev.miles > 0
          ? `  (${ev.miles.toFixed(1)} mi)`
          : ''
        const noteStr = ev.note ? `  — ${ev.note}` : ''
        const line = `${ev.start}–${ev.end}   ${ev.location}${noteStr}${milesStr}`
        return (
          <g key={i}>
            <text x={PAD + 10} y={y + 12} fontSize={10}
                  fill="#1e293b" fontFamily="Arial,sans-serif">
              {line}
            </text>
            <line x1={PAD + 6} y1={y + 15} x2={W - PAD - 6} y2={y + 15}
                  stroke="#e2e8f0" strokeWidth={0.5} />
          </g>
        )
      })}
      {events.length > MAX_REMARKS && (
        <text x={PAD + 10} y={REM_TOP + REM_HDR_H + 4 + MAX_REMARKS * REM_LINE_H + 10}
              fontSize={9} fill="#94a3b8" fontFamily="Arial,sans-serif">
          … {events.length - MAX_REMARKS} additional events not shown
        </text>
      )}

      {/* ════════════════════════════════════════════════════════
          SHIPPING DOCUMENTS
          ════════════════════════════════════════════════════════ */}

      <rect x={PAD} y={SHIP_TOP} width={W - PAD * 2} height={SHIP_H}
            fill="none" stroke="#94a3b8" strokeWidth={0.6} />
      <rect x={PAD} y={SHIP_TOP} width={W - PAD * 2} height={18} fill="#f1f5f9" />
      <text x={PAD + 8} y={SHIP_TOP + 13} fontSize={11} fontWeight="bold"
            fill="#1e3a8a" fontFamily="Arial,sans-serif">
        SHIPPING DOCUMENTS — DVL or Manifest No., Shipper &amp; Commodity
      </text>

      <HdrField label="Bill of Lading / Manifest No." value="—" x={PAD + 8}  y={SHIP_TOP + 26} w={270} />
      <HdrField label="Shipper"                        value="—" x={320}      y={SHIP_TOP + 26} w={230} />
      <HdrField label="Commodity"                      value="—" x={590}      y={SHIP_TOP + 26} w={220} />

      {/* ════════════════════════════════════════════════════════
          RECAP (70 hr / 8 day)
          ════════════════════════════════════════════════════════ */}

      <rect x={PAD} y={RECAP_TOP} width={W - PAD * 2} height={RECAP_H}
            fill="none" stroke="#94a3b8" strokeWidth={0.6} />

      {/* Recap header bar */}
      <rect x={PAD} y={RECAP_TOP} width={W - PAD * 2} height={20} fill="#1e3a8a" />
      <text x={W / 2} y={RECAP_TOP + 14} textAnchor="middle"
            fontSize={11} fontWeight="bold" fill="white" fontFamily="Arial,sans-serif">
        RECAP
      </text>

      {/* Divider between 70/8 and 60/7 columns */}
      <line x1={W / 2} y1={RECAP_TOP + 20} x2={W / 2} y2={RECAP_TOP + RECAP_H}
            stroke="#cbd5e1" strokeWidth={0.6} />

      {/* 70-hr / 8-day column */}
      <RecapCol
        x={PAD + 12}
        y={RECAP_TOP + 20}
        title="70 Hour / 8 Day Rule"
        rows={[
          ['On-duty hours today',          fmtR(recap.on_duty_hours_today)],
          ['On-duty hours previous 7 days', fmtR(recap.on_duty_hours_previous_7_days)],
          ['Total on-duty hours (8 days)', fmtR(recap.total_on_duty_8_days)],
          ['Hours available after today',  fmtR(recap.hours_available_tomorrow)],
        ]}
      />

      {/* 60-hr / 7-day column (placeholder — app uses 70/8) */}
      <RecapCol
        x={W / 2 + 12}
        y={RECAP_TOP + 20}
        title="60 Hour / 7 Day Rule (not applicable)"
        rows={[
          ['On-duty hours today',          fmtH(onDutyH)],
          ['On-duty hours previous 6 days','—'],
          ['Total on-duty hours (7 days)', '—'],
          ['Hours available after today',  '—'],
        ]}
      />
    </svg>
  )
}
