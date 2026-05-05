import { useState, useCallback } from 'react'

export function useSelection() {
  const [selected, setSelected] = useState(null)
  // selected = { timestamp, forecast_energy, optimized_energy, index }

  const select   = useCallback((item) => setSelected(item),  [])
  const deselect = useCallback(()     => setSelected(null),  [])

  return { selected, select, deselect }
}