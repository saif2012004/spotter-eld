# Prompt 6 — Daily Log Sheet SVG (the visually impressive part)

Implement `frontend/src/components/DailyLogSheet.jsx`.

This must render a faithful reproduction of the FMCSA Driver's Daily Log paper form using SVG.

## Reference layout

- **Header**: "Driver's Daily Log (24 hours)" with date, From/To, Total Miles Driving Today, Total Mileage Today, Carrier Name, Main Office Address, Truck/Trailer numbers, Home Terminal Address
- **Main grid**: 24-hour timeline horizontally (Midnight to Midnight, with Noon labeled in the middle), 4 horizontal rows labeled:
    1. Off Duty
    2. Sleeper Berth
    3. Driving
    4. On Duty (not driving)
- Each hour subdivided into 4 fifteen-minute ticks
- "Total Hours" column on the right
- **Remarks section** below the grid with horizontal lines
- **Shipping Documents** section (DVL or Manifest No., Shipper & Commodity)
- **Recap** at the bottom (70hr/8day and 60hr/7day boxes — render but leave the 60/7 side mostly empty since we're 70/8)

## Component props

- `dailyLog`: `{ date, events, totals, miles_today }` (one day's worth)
- `carrierName`, `carrierAddress`, `truckNumbers`, `homeTerminal` (optional, fall back to placeholder text)

## Drawing the duty status line

- Compute each event's start/end as fractional hours from midnight (e.g., 8:30 = 8.5, 14:15 = 14.25)
- For each event, draw a horizontal line on the row matching `event.status`
- Between consecutive events with different statuses, draw a vertical connecting line
- The result is the classic step-line pattern truckers draw on paper logs
- Stroke: black, 2px

## Sizing

Use `viewBox` so the SVG scales. Width ~1100, height ~600 for the grid area, more for header and remarks. Make it printable (each log sheet on its own page when `window.print()` is called — add a CSS `@media print` rule to App.

## Remarks

List event notes with their times: "08:00–09:00 Pickup at Phoenix, AZ", "12:00–12:15 Fuel stop", etc.

## Totals

Fill totals on the right side: `off_duty`, `sleeper`, `driving`, `on_duty_not_driving` — each rounded to 0.25 hr.

## Integration

Wire up `App.jsx` so it renders one `DailyLogSheet` per item in `tripData.daily_logs`, vertically stacked, with a "Print all logs" button at the top that calls `window.print()`.

Make it look good. This is the most visually distinctive part of the app and the assessment specifically grades on UI/UX.
