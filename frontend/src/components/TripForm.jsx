import React, { useState } from 'react'

const DEFAULTS = {
  current_location: 'Los Angeles, CA',
  pickup_location:  'Phoenix, AZ',
  dropoff_location: 'Dallas, TX',
  cycle_used_hours: '20',
}

function validate(fields) {
  const errors = {}
  if (!fields.current_location.trim()) errors.current_location = 'Required'
  if (!fields.pickup_location.trim())  errors.pickup_location  = 'Required'
  if (!fields.dropoff_location.trim()) errors.dropoff_location = 'Required'
  const h = parseFloat(fields.cycle_used_hours)
  if (isNaN(h) || h < 0 || h > 70)
    errors.cycle_used_hours = 'Must be a number between 0 and 70'
  return errors
}

export default function TripForm({ onSubmit, loading }) {
  const [fields, setFields] = useState(DEFAULTS)
  const [errors, setErrors] = useState({})

  function handleChange(e) {
    setFields((prev) => ({ ...prev, [e.target.name]: e.target.value }))
    if (errors[e.target.name]) {
      setErrors((prev) => ({ ...prev, [e.target.name]: undefined }))
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    const errs = validate(fields)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setErrors({})
    onSubmit({
      current_location: fields.current_location.trim(),
      pickup_location:  fields.pickup_location.trim(),
      dropoff_location: fields.dropoff_location.trim(),
      cycle_used_hours: parseFloat(fields.cycle_used_hours),
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Field
        label="Current Location"
        name="current_location"
        value={fields.current_location}
        error={errors.current_location}
        onChange={handleChange}
        placeholder="e.g. Chicago, IL"
      />
      <Field
        label="Pickup Location"
        name="pickup_location"
        value={fields.pickup_location}
        error={errors.pickup_location}
        onChange={handleChange}
        placeholder="e.g. Memphis, TN"
      />
      <Field
        label="Dropoff Location"
        name="dropoff_location"
        value={fields.dropoff_location}
        error={errors.dropoff_location}
        onChange={handleChange}
        placeholder="e.g. Atlanta, GA"
      />

      <div className="form-group">
        <label htmlFor="cycle_used_hours">Cycle Hours Used (0 – 70)</label>
        <input
          id="cycle_used_hours"
          type="number"
          name="cycle_used_hours"
          value={fields.cycle_used_hours}
          onChange={handleChange}
          min="0"
          max="70"
          step="0.5"
          className={errors.cycle_used_hours ? 'input-error' : ''}
        />
        {errors.cycle_used_hours && (
          <p className="field-error">{errors.cycle_used_hours}</p>
        )}
      </div>

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? (
          <>
            <span className="spinner" aria-hidden="true" />
            Planning…
          </>
        ) : (
          'Plan Trip'
        )}
      </button>
    </form>
  )
}

function Field({ label, name, value, error, onChange, placeholder }) {
  return (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        type="text"
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={error ? 'input-error' : ''}
        autoComplete="off"
      />
      {error && <p className="field-error">{error}</p>}
    </div>
  )
}
