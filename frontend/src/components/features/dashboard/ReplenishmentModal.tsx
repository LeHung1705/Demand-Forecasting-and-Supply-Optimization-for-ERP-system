import React from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material'

type Props = { open: boolean; onClose: () => void }

export default function ReplenishmentModal({ open, onClose }: Props) {
  const rows = [
    { store: 'Store 1', sku: 'SKU-001', qty: 120 },
    { store: 'Store 2', sku: 'SKU-045', qty: 60 },
  ]

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Replenishment Plan</DialogTitle>
      <DialogContent>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Store</TableCell>
              <TableCell>SKU</TableCell>
              <TableCell>Qty</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r, i) => (
              <TableRow key={i}><TableCell>{r.store}</TableCell><TableCell>{r.sku}</TableCell><TableCell>{r.qty}</TableCell></TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => { console.log('export plan'); onClose() }}>Export CSV</Button>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}
