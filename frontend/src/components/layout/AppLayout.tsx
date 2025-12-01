import React from 'react'
import { Container, Box } from '@mui/material'

type Props = {
  children?: React.ReactNode
}

export default function AppLayout({ children }: Props) {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {children}
      </Container>
    </Box>
  )
}
