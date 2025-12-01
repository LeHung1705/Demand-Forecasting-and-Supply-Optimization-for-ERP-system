import React from 'react'
import { Paper } from '@mui/material'

export default function AppCard({ children, sx }: any) {
  return (
    <Paper sx={{ p: 2, borderRadius: 2, ...sx }} elevation={1}>
      {children}
    </Paper>
  )
}
