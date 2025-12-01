import React from 'react'
import { Dialog, DialogTitle, DialogContent } from '@mui/material'

export default function AppModal({ open, onClose, title, children }: any) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      {title && <DialogTitle>{title}</DialogTitle>}
      <DialogContent>{children}</DialogContent>
    </Dialog>
  )
}
