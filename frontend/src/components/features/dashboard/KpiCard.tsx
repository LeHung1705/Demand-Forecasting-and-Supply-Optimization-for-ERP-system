import React from 'react'
import { Card, CardContent, Typography } from '@mui/material'

type Props = {
  label: string
  value: React.ReactNode
}

export default function KpiCard({ label, value }: Props) {
  return (
    <Card sx={{ borderRadius: 2, boxShadow: 2, height: '100%' }}>
      <CardContent sx={{ py: 1.5 }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 700, mt: 0.5 }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  )
}