import React from 'react'
import { Card, CardContent, Typography, Grid, FormControl, InputLabel, Select, MenuItem, FormControlLabel, Switch, Accordion, AccordionSummary, AccordionDetails, Slider, Box } from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useDashboardState } from '../../../hooks/useDashboardState'

export default function ControlPanel() {
  const { aggregation, setAggregation, showStockout, setShowStockout, showRecovered, setShowRecovered, showForecastCI, setShowForecastCI } = useDashboardState()

  return (
    <Card sx={{ mb: 2, borderRadius: 2, boxShadow: 2 }}>
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Control Panel</Typography>
        <Grid container spacing={2} sx={{ mt: 1, alignItems: 'center' }}>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Aggregation</InputLabel>
              <Select value={aggregation} label="Aggregation" onChange={e => setAggregation(e.target.value as any)}>
                <MenuItem value="hourly">Hourly</MenuItem>
                <MenuItem value="daily">Daily</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControlLabel
              control={<Switch checked={showStockout} onChange={e => setShowStockout(e.target.checked)} />}
              label={<Typography variant="body2">Show Stockout Hours</Typography>}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControlLabel
              control={<Switch checked={showRecovered} onChange={e => setShowRecovered(e.target.checked)} />}
              label={<Typography variant="body2">Show Recovered Demand</Typography>}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControlLabel
              control={<Switch checked={showForecastCI} onChange={e => setShowForecastCI(e.target.checked)} />}
              label={<Typography variant="body2">Show Forecast (CI)</Typography>}
            />
          </Grid>
        </Grid>

        <Accordion sx={{ mt: 2, boxShadow: 'none' }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ pl: 0 }}>Advanced</AccordionSummary>
          <AccordionDetails>
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>Model selection</Typography>
              <FormControl fullWidth size="small">
                <Select defaultValue="model-a">
                  <MenuItem value="model-a">Model A (basic)</MenuItem>
                  <MenuItem value="model-b">Model B (sota)</MenuItem>
                </Select>
              </FormControl>

              <Box sx={{ mt: 2 }}>
                <Typography variant="caption">Model param: sensitivity</Typography>
                <Slider defaultValue={50} min={0} max={100} />
              </Box>
            </Box>
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  )
}
