import 'vite/modulepreload-polyfill'
import { useState, useEffect, useCallback } from 'react'
import {
    Box, Typography, Grid, MenuItem, Select, FormControl, InputLabel,
    TextField, Button, Divider, CircularProgress, Alert, Chip, Stack,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import Base from '../../src/components/Base.jsx'
import render, { useAppContext } from '../../src/render.jsx'
import apiClient from '../../src/apiClient.js'
import { BarChart, LineChart } from '@mui/x-charts'

// ─── helpers ────────────────────────────────────────────────────────────────

function today() {
    return new Date().toISOString().slice(0, 10)
}
function daysAgo(n) {
    const d = new Date()
    d.setDate(d.getDate() - n)
    return d.toISOString().slice(0, 10)
}

function NoData({ message }) {
    return (
        <Box sx={{ py: 6, textAlign: 'center' }}>
            <Typography color="text.secondary" variant="body2">{message}</Typography>
        </Box>
    )
}

function SectionTitle({ children }) {
    return (
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            {children}
        </Typography>
    )
}

function ChartCard({ title, children }) {
    return (
        <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>{title}</Typography>
            {children}
        </Box>
    )
}

// STATUS_LABEL maps backend status values to display labels (filled in from localeMessages)
const STATUS_COLORS = {
    active: '#636eec',
    completed: '#4caf50',
    deactivated: '#ef5350',
    delivered: '#4caf50',
    scheduled: '#90caf9',
    processing: '#ffa726',
    canceled: '#bdbdbd',
    blocked: '#ef5350',
    failed: '#ef5350',
}

// ─── main component ─────────────────────────────────────────────────────────

function Analytics() {
    const { apiBaseUrl, analyticsBaseUrl, localeMessages, direction } = useAppContext()

    // filters
    const [courses, setCourses] = useState([])
    const [selectedCourses, setSelectedCourses] = useState([])
    const [dateFrom, setDateFrom] = useState(daysAgo(29))
    const [dateTo, setDateTo] = useState(today())
    const [granularity, setGranularity] = useState('day')

    // data
    const [enrollmentsOverTime, setEnrollmentsOverTime] = useState(null)
    const [statusBreakdown, setStatusBreakdown] = useState(null)
    const [funnel, setFunnel] = useState(null)
    const [avgProgress, setAvgProgress] = useState(null)
    const [timeToComplete, setTimeToComplete] = useState(null)
    const [deliveryOverTime, setDeliveryOverTime] = useState(null)
    const [deliveryStatus, setDeliveryStatus] = useState(null)
    const [openRate, setOpenRate] = useState(null)

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const params = useCallback(() => {
        const p = new URLSearchParams()
        selectedCourses.forEach(id => p.append('course_id', id))
        p.set('date_from', dateFrom)
        p.set('date_to', dateTo)
        p.set('granularity', granularity)
        return p.toString()
    }, [selectedCourses, dateFrom, dateTo, granularity])

    useEffect(() => {
        apiClient.get(`${apiBaseUrl}/organizations/${analyticsBaseUrl.orgId}/courses`)
            .then(d => setCourses(d.courses || []))
            .catch(() => {})
    }, [])

    const fetchAll = useCallback(() => {
        setLoading(true)
        setError(null)
        const q = params()
        const base = `${analyticsBaseUrl.base}`
        Promise.all([
            apiClient.get(`${base}/enrollments/over-time/?${q}`),
            apiClient.get(`${base}/enrollments/status-breakdown/?${q}`),
            apiClient.get(`${base}/completion-funnel/?${q}`),
            apiClient.get(`${base}/progress/?${q}`),
            apiClient.get(`${base}/time-to-complete/?${q}`),
            apiClient.get(`${base}/email-delivery/over-time/?${q}`),
            apiClient.get(`${base}/email-delivery/status-breakdown/?${q}`),
            apiClient.get(`${base}/email-open-rate/?${q}`),
        ])
            .then(([eot, sb, f, ap, ttc, dot, ds, or_]) => {
                setEnrollmentsOverTime(eot.data)
                setStatusBreakdown(sb.data)
                setFunnel(f.data)
                setAvgProgress(ap.data)
                setTimeToComplete(ttc.data)
                setDeliveryOverTime(dot.data)
                setDeliveryStatus(ds.data)
                setOpenRate(or_.data)
            })
            .catch(() => setError(true))
            .finally(() => setLoading(false))
    }, [params, analyticsBaseUrl])

    useEffect(() => { fetchAll() }, [])

    const download = (endpoint) => {
        const q = params()
        window.location.href = `${analyticsBaseUrl.base}/${endpoint}/?${q}`
    }

    // ── chart helpers ──────────────────────────────────────────────────────

    const TimeSeriesChart = ({ data, color = '#636eec' }) => {
        if (!data?.length) return <NoData message={localeMessages.no_data} />
        return (
            <LineChart
                xAxis={[{ scaleType: 'band', data: data.map(r => r.period), tickLabelStyle: { fontSize: 11 } }]}
                series={[{ data: data.map(r => r.count), color, area: true }]}
                height={200}
                margin={{ left: 40, right: 10, top: 10, bottom: 40 }}
            />
        )
    }

    const StatusBreakdownChart = ({ data }) => {
        if (!data?.length) return <NoData message={localeMessages.no_data} />
        // Group by course, stack by status
        const courseMap = {}
        const statuses = [...new Set(data.map(r => r.status))]
        data.forEach(r => {
            if (!courseMap[r.course_title]) courseMap[r.course_title] = {}
            courseMap[r.course_title][r.status] = r.count
        })
        const courseLabels = Object.keys(courseMap)
        return (
            <BarChart
                xAxis={[{ scaleType: 'band', data: courseLabels, tickLabelStyle: { fontSize: 11 } }]}
                series={statuses.map(s => ({
                    label: localeMessages[s] || s,
                    data: courseLabels.map(c => courseMap[c][s] || 0),
                    color: STATUS_COLORS[s],
                    stack: 'total',
                }))}
                height={200}
                margin={{ left: 40, right: 10, top: 10, bottom: 60 }}
            />
        )
    }

    const FunnelChart = ({ data }) => {
        if (!data?.length) return <NoData message={localeMessages.no_data} />
        return (
            <BarChart
                layout="horizontal"
                yAxis={[{ scaleType: 'band', data: data.map(r => r.title), tickLabelStyle: { fontSize: 11 } }]}
                series={[{ data: data.map(r => r.learners_reached), color: '#636eec', label: localeMessages.learners_reached }]}
                height={Math.max(180, data.length * 36)}
                margin={{ left: 140, right: 20, top: 10, bottom: 30 }}
            />
        )
    }

    const ProgressChart = ({ data }) => {
        if (!data?.length) return <NoData message={localeMessages.no_data} />
        return (
            <BarChart
                xAxis={[{ scaleType: 'band', data: data.map(r => r.course_title), tickLabelStyle: { fontSize: 11 } }]}
                series={[{ data: data.map(r => r.average_progress), color: '#636eec', label: '%' }]}
                height={200}
                margin={{ left: 40, right: 10, top: 10, bottom: 60 }}
            />
        )
    }

    const TimeToCompleteChart = ({ data }) => {
        if (!data?.length) return <NoData message={localeMessages.no_data} />
        return (
            <Stack spacing={1}>
                {data.map(row => (
                    <Box key={row.course_id} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Typography variant="body2" sx={{ minWidth: 160, fontWeight: 500 }} noWrap>{row.course_title}</Typography>
                        <Typography variant="body2" color="text.secondary">
                            {localeMessages.average_days}: <strong>{row.average_days ?? '–'}</strong>
                            &nbsp;·&nbsp;{row.total_completions} {localeMessages.completed}
                        </Typography>
                    </Box>
                ))}
            </Stack>
        )
    }

    const OpenRateChart = ({ data }) => {
        if (!data?.length) return <NoData message={localeMessages.no_data} />
        return (
            <Stack spacing={1.5}>
                {data.map(row => (
                    <Box key={row.course_id}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="body2" noWrap sx={{ maxWidth: '70%' }}>{row.course_title}</Typography>
                            <Typography variant="body2" fontWeight={600}>{row.open_rate}%</Typography>
                        </Box>
                        <Box sx={{ height: 6, borderRadius: 3, bgcolor: 'action.hover', overflow: 'hidden' }}>
                            <Box sx={{ height: '100%', width: `${row.open_rate}%`, bgcolor: '#636eec', borderRadius: 3 }} />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                            {row.total_opened} / {row.total_delivered} {localeMessages.email_open_rate}
                        </Typography>
                    </Box>
                ))}
            </Stack>
        )
    }

    // ── render ─────────────────────────────────────────────────────────────
    return (
        <Base breadCrumbList={[{ label: localeMessages.analytics, href: '#' }]}>
            <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1400, mx: 'auto' }}>
                <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
                    {localeMessages.analytics}
                </Typography>

                {/* Filters */}
                <Box sx={{ p: 2, mb: 3, borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>{localeMessages.filters}</Typography>
                    <Grid container spacing={2} alignItems="flex-end">
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <FormControl fullWidth size="small">
                                <InputLabel>{localeMessages.course}</InputLabel>
                                <Select
                                    multiple
                                    value={selectedCourses}
                                    onChange={e => setSelectedCourses(e.target.value)}
                                    label={localeMessages.course}
                                    renderValue={selected => (
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                            {selected.map(id => (
                                                <Chip key={id} size="small"
                                                    label={courses.find(c => c.id === id)?.title || id} />
                                            ))}
                                        </Box>
                                    )}
                                >
                                    {courses.map(c => (
                                        <MenuItem key={c.id} value={c.id}>{c.title}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                            <TextField
                                fullWidth size="small" type="date" label={localeMessages.date_from}
                                value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                                slotProps={{ inputLabel: { shrink: true } }}
                            />
                        </Grid>
                        <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                            <TextField
                                fullWidth size="small" type="date" label={localeMessages.date_to}
                                value={dateTo} onChange={e => setDateTo(e.target.value)}
                                slotProps={{ inputLabel: { shrink: true } }}
                            />
                        </Grid>
                        <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                            <FormControl fullWidth size="small">
                                <InputLabel>{localeMessages.granularity}</InputLabel>
                                <Select value={granularity} onChange={e => setGranularity(e.target.value)} label={localeMessages.granularity}>
                                    <MenuItem value="day">{localeMessages.day}</MenuItem>
                                    <MenuItem value="week">{localeMessages.week}</MenuItem>
                                    <MenuItem value="month">{localeMessages.month}</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                            <Button fullWidth variant="contained" onClick={fetchAll} disabled={loading}>
                                {loading ? <CircularProgress size={18} color="inherit" /> : localeMessages.apply}
                            </Button>
                        </Grid>
                    </Grid>
                </Box>

                {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load analytics data.</Alert>}

                {/* Downloads */}
                <Box sx={{ mb: 3 }}>
                    <SectionTitle>{localeMessages.downloads}</SectionTitle>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {[
                            { key: 'downloads/learner-progress', label: localeMessages.download_learner_progress },
                            { key: 'downloads/delivery-log', label: localeMessages.download_delivery_log },
                            { key: 'downloads/completion-summary', label: localeMessages.download_completion_summary },
                        ].map(({ key, label }) => (
                            <Button key={key} variant="outlined" size="small"
                                startIcon={<DownloadIcon />}
                                onClick={() => download(key)}>
                                {label}
                            </Button>
                        ))}
                    </Stack>
                </Box>

                <Divider sx={{ mb: 3 }} />

                {/* Charts — row 1: enrolments + status */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.enrollments_over_time}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <TimeSeriesChart data={enrollmentsOverTime} />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.enrollment_status_breakdown}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <StatusBreakdownChart data={statusBreakdown} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Charts — row 2: delivery over time + delivery status */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.email_delivery_over_time}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <TimeSeriesChart data={deliveryOverTime} color="#4caf50" />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.email_delivery_status_breakdown}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <StatusBreakdownChart data={deliveryStatus} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Charts — row 3: funnel + open rate */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.completion_funnel}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <FunnelChart data={funnel} />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.email_open_rate}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <OpenRateChart data={openRate} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Charts — row 4: avg progress + time to complete */}
                <Grid container spacing={3}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.average_progress}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <ProgressChart data={avgProgress} />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.time_to_complete}>
                            {loading ? <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
                                : <TimeToCompleteChart data={timeToComplete} />}
                        </ChartCard>
                    </Grid>
                </Grid>
            </Box>
        </Base>
    )
}

render(<Analytics />)
