import 'vite/modulepreload-polyfill'
import { useState, useEffect, useCallback } from 'react'
import {
    Box, Typography, Grid, MenuItem, Select, FormControl, InputLabel,
    TextField, Button, CircularProgress, Alert, Chip, Stack, Tooltip,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import Base from '../../src/components/Base.jsx'
import render, { useAppContext } from '../../src/render.jsx';
import apiClient from '../../src/apiClient.js'
import { BarChart, LineChart, PieChart } from '@mui/x-charts'

// ─── helpers ────────────────────────────────────────────────────────────────

function today() {
    return new Date().toISOString().slice(0, 10)
}
function daysAgo(n) {
    const d = new Date()
    d.setDate(d.getDate() - n)
    return d.toISOString().slice(0, 10)
}

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

// ─── shared UI ───────────────────────────────────────────────────────────────

function NoData({ message }) {
    return (
        <Box sx={{ py: 6, textAlign: 'center' }}>
            <Typography color="text.secondary" variant="body2">{message}</Typography>
        </Box>
    )
}

function ChartCard({ title, tooltip, children }) {
    return (
        <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{title}</Typography>
                {tooltip && (
                    <Tooltip title={tooltip} placement="top" arrow>
                        <InfoOutlinedIcon sx={{ fontSize: '1rem', color: 'text.secondary', cursor: 'help', flexShrink: 0 }} />
                    </Tooltip>
                )}
            </Box>
            {children}
        </Box>
    )
}

function ChartLoading() {
    return <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress size={28} /></Box>
}

// ─── chart components (defined at module level — never inside a component) ───

function TimeSeriesChart({ data, color = '#636eec', noDataMessage }) {
    if (!data?.length) return <NoData message={noDataMessage} />
    return (
        <LineChart
            xAxis={[{ scaleType: 'band', data: data.map(r => r.period), tickLabelStyle: { fontSize: 11 } }]}
            series={[{ data: data.map(r => r.count), color, area: true }]}
            height={200}
            margin={{ left: 40, right: 10, top: 10, bottom: 40 }}
        />
    )
}

function StatusBreakdownChart({ data, localeMessages, noDataMessage }) {
    if (!data?.length) return <NoData message={noDataMessage} />

    // Aggregate counts across all courses by status
    const totals = {}
    data.forEach(r => { totals[r.status] = (totals[r.status] || 0) + r.count })
    const pieData = Object.entries(totals).map(([status, count]) => ({
        id: status,
        value: count,
        label: `${localeMessages[status] || status} (${count})`,
        color: STATUS_COLORS[status],
    }))

    return (
        <PieChart
            height={220}
            series={[{
                data: pieData,
                innerRadius: '45%',
                arcLabel: (item) => `${item.value}`,
                arcLabelMinAngle: 20,
                highlightScope: { fade: 'global', highlight: 'item' },
            }]}
            margin={{ bottom: 30, top: 10, left: 10, right: 10 }}
            slotProps={{
                legend: {
                    direction: 'row',
                    position: { vertical: 'bottom', horizontal: 'middle' },
                    padding: 0,
                    itemMarkWidth: 10,
                    itemMarkHeight: 10,
                    markGap: 5,
                    itemGap: 12,
                },
            }}
        />
    )
}

function FunnelGroup({ items, learnersReachedLabel }) {
    const max = Math.max(...items.map(r => r.learners_reached), 1)
    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            {items.map(row => (
                <Box key={row.course_content_id} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Typography
                        variant="body2"
                        sx={{ minWidth: 180, width: 180, flexShrink: 0, fontSize: '0.8rem', lineHeight: 1.3 }}
                        title={row.title}
                    >
                        {row.title}
                    </Typography>
                    <Box sx={{ flex: 1, bgcolor: 'action.hover', borderRadius: 1, overflow: 'hidden', height: 18 }}>
                        <Box sx={{
                            height: '100%',
                            width: `${(row.learners_reached / max) * 100}%`,
                            bgcolor: '#636eec',
                            borderRadius: 1,
                            minWidth: row.learners_reached > 0 ? 4 : 0,
                        }} />
                    </Box>
                    <Typography variant="body2" sx={{ minWidth: 32, textAlign: 'right', fontSize: '0.8rem', fontWeight: 600, color: 'text.secondary' }}>
                        {row.learners_reached}
                    </Typography>
                </Box>
            ))}
        </Box>
    )
}

function FunnelChart({ data, learnersReachedLabel, noDataMessage }) {
    if (!data?.length) return <NoData message={noDataMessage} />

    // Group by course, preserving priority order within each group
    const courseMap = {}
    data.forEach(item => {
        if (!courseMap[item.course_id]) courseMap[item.course_id] = { title: item.course_title, items: [] }
        courseMap[item.course_id].items.push(item)
    })
    const groups = Object.values(courseMap).map(group => ({
        ...group,
        items: [...group.items].sort((a, b) => a.priority - b.priority),
    }))

    if (groups.length === 1) {
        return <FunnelGroup items={groups[0].items} learnersReachedLabel={learnersReachedLabel} />
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {groups.map(group => (
                <Box key={group.title}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                        {group.title}
                    </Typography>
                    <FunnelGroup items={group.items} learnersReachedLabel={learnersReachedLabel} />
                </Box>
            ))}
        </Box>
    )
}

function ProgressChart({ data, noDataMessage }) {
    if (!data?.length) return <NoData message={noDataMessage} />
    return (
        <BarChart
            xAxis={[{ scaleType: 'band', data: data.map(r => r.course_title), tickLabelStyle: { fontSize: 11 } }]}
            yAxis={[{ min: 0, max: 100 }]}
            series={[{
                data: data.map(r => r.average_progress),
                color: '#636eec',
                label: '%',
                valueFormatter: (v) => `${v}%`,
            }]}
            height={220}
            margin={{ left: 40, right: 10, top: 10, bottom: 60 }}
        />
    )
}

function TimeToCompleteChart({ data, averageDaysLabel, completedLabel, noDataMessage }) {
    if (!data?.length) return <NoData message={noDataMessage} />
    return (
        <Stack spacing={1}>
            {data.map(row => (
                <Box key={row.course_id} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography variant="body2" sx={{ minWidth: 160, fontWeight: 500 }} noWrap>
                        {row.course_title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {averageDaysLabel}: <strong>{row.average_days ?? '–'}</strong>
                        &nbsp;·&nbsp;{row.total_completions} {completedLabel}
                    </Typography>
                </Box>
            ))}
        </Stack>
    )
}

function OpenRateChart({ data, openRateLabel, noDataMessage }) {
    if (!data?.length) return <NoData message={noDataMessage} />
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
                        {row.total_opened} / {row.total_delivered} {openRateLabel}
                    </Typography>
                </Box>
            ))}
        </Stack>
    )
}

// ─── main component ─────────────────────────────────────────────────────────

function Analytics() {
    const { apiBaseUrl, analyticsBaseUrl, localeMessages } = useAppContext()

    const [courses, setCourses] = useState([])
    const [selectedCourses, setSelectedCourses] = useState([])
    const [dateFrom, setDateFrom] = useState(daysAgo(29))
    const [dateTo, setDateTo] = useState(today())
    const [granularity, setGranularity] = useState('day')

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

    const buildParams = useCallback(() => {
        const p = new URLSearchParams()
        selectedCourses.forEach(id => p.append('course_id', id))
        p.set('date_from', dateFrom)
        p.set('date_to', dateTo)
        p.set('granularity', granularity)
        return p.toString()
    }, [selectedCourses, dateFrom, dateTo, granularity])

    useEffect(() => {
        apiClient.get(`${apiBaseUrl}/organizations/${analyticsBaseUrl.orgId}/courses/`)
            .then(d => setCourses(d.courses || []))
            .catch(() => {})
    }, [apiBaseUrl, analyticsBaseUrl.orgId])

    const fetchAll = useCallback(() => {
        setLoading(true)
        setError(null)
        const q = buildParams()
        const base = analyticsBaseUrl.base
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
    }, [buildParams, analyticsBaseUrl.base])

    useEffect(() => { fetchAll() }, [fetchAll])

    const download = useCallback((endpoint) => {
        const q = buildParams()
        window.location.href = `${analyticsBaseUrl.base}/${endpoint}/?${q}`
    }, [buildParams, analyticsBaseUrl.base])

    const noData = localeMessages.no_data

    return (
        <Base breadCrumbList={[{ label: localeMessages.analytics, href: '#' }]}>
            <Grid size={{ xs: 12 }} sx={{ py: 2, pl: { xs: 0, sm: 2 } }}>
            <Box sx={{ p: { xs: 1, sm: 2 }, mb: 2, borderRadius: { xs: 0, sm: 2 }, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)' }}>

                {/* Filters */}
                <Box sx={{ mb: 3 }}>
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
                            <TextField fullWidth size="small" type="date" label={localeMessages.date_from}
                                value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                                slotProps={{ inputLabel: { shrink: true } }} />
                        </Grid>
                        <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                            <TextField fullWidth size="small" type="date" label={localeMessages.date_to}
                                value={dateTo} onChange={e => setDateTo(e.target.value)}
                                slotProps={{ inputLabel: { shrink: true } }} />
                        </Grid>
                        <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                            <FormControl fullWidth size="small">
                                <InputLabel>{localeMessages.granularity}</InputLabel>
                                <Select value={granularity} onChange={e => setGranularity(e.target.value)}
                                    label={localeMessages.granularity}>
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
                <Box sx={{ mb: 3, pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>{localeMessages.downloads}</Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {[
                            { key: 'downloads/learner-progress', label: localeMessages.download_learner_progress },
                            { key: 'downloads/delivery-log', label: localeMessages.download_delivery_log },
                            { key: 'downloads/completion-summary', label: localeMessages.download_completion_summary },
                        ].map(({ key, label }) => (
                            <Button key={key} variant="outlined" size="small"
                                startIcon={<DownloadIcon />} onClick={() => download(key)}>
                                {label}
                            </Button>
                        ))}
                    </Stack>
                </Box>

                {/* Row 1 */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.enrollments_over_time}>
                            {loading ? <ChartLoading /> : <TimeSeriesChart data={enrollmentsOverTime} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.enrollment_status_breakdown}>
                            {loading ? <ChartLoading /> : <StatusBreakdownChart data={statusBreakdown} localeMessages={localeMessages} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Row 2 */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.email_delivery_over_time}>
                            {loading ? <ChartLoading /> : <TimeSeriesChart data={deliveryOverTime} color="#4caf50" noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.email_delivery_status_breakdown}>
                            {loading ? <ChartLoading /> : <StatusBreakdownChart data={deliveryStatus} localeMessages={localeMessages} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Row 3 — funnel full width */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12 }}>
                        <ChartCard title={localeMessages.completion_funnel} tooltip={localeMessages.completion_funnel_tooltip}>
                            {loading ? <ChartLoading /> : <FunnelChart data={funnel} learnersReachedLabel={localeMessages.learners_reached} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Row 4 — open rate full width */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid size={{ xs: 12 }}>
                        <ChartCard title={localeMessages.email_open_rate}>
                            {loading ? <ChartLoading /> : <OpenRateChart data={openRate} openRateLabel={localeMessages.email_open_rate} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                </Grid>

                {/* Row 5 */}
                <Grid container spacing={3}>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.average_progress}>
                            {loading ? <ChartLoading /> : <ProgressChart data={avgProgress} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                        <ChartCard title={localeMessages.time_to_complete}>
                            {loading ? <ChartLoading /> : <TimeToCompleteChart data={timeToComplete} averageDaysLabel={localeMessages.average_days} completedLabel={localeMessages.completed} noDataMessage={noData} />}
                        </ChartCard>
                    </Grid>
                </Grid>
            </Box>
            </Grid>
        </Base>
    )
}

render({children: <Analytics />})
