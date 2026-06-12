import { Box, Grid, Skeleton, Typography } from '@mui/material';
import { PieChart } from '@mui/x-charts/PieChart';
import { BarChart } from '@mui/x-charts/BarChart';
import { useTheme } from '@mui/material/styles';

function CourseAnalyticsSection({
    localeMessages,
    totalEnrollments,
    isEnrollmentsLoading,
    hasEnrollmentsChartData,
    enrollmentsPieData,
    isWeeklyStatsLoading,
    hasWeeklyChartData,
    weeklyStats,
}) {
    const theme = useTheme();

    return (
        <Grid container spacing={3} sx={{ alignItems: 'stretch' }}>
            <Grid size={{ xs: 12, lg: 6 }} sx={{ display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ py: 3, borderRadius: { xs: 0, sm: 2 }, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', flex: 1 }}>
                    <Typography variant="h6" align="center">{localeMessages['enrollments_distribution']}</Typography>
                    <Typography variant="body2" align="center" sx={{ mt: 1, mb: 2, color: 'text.secondary' }}>
                        {(localeMessages['total_enrollments']) + ': ' + totalEnrollments}
                    </Typography>
                    {isEnrollmentsLoading ? (
                        <Box sx={{ px: 2 }}>
                            <Skeleton variant="circular" width={180} height={180} sx={{ mx: 'auto', my: 2 }} />
                            <Skeleton variant="text" width="80%" sx={{ mx: 'auto' }} />
                            <Skeleton variant="text" width="60%" sx={{ mx: 'auto' }} />
                        </Box>
                    ) : hasEnrollmentsChartData ? (
                        <PieChart
                            height={300}
                            series={[
                                {
                                    data: enrollmentsPieData,
                                    innerRadius: '50%',
                                    arcLabelMinAngle: 20,
                                    highlightScope: { fade: 'global', highlight: 'item' },
                                },
                            ]}
                            skipAnimation={false}
                            margin={{
                                bottom: 20,
                                top: 20,
                                left: 5,
                                right: 5,
                            }}
                            slotProps={{
                                legend: {
                                    direction: 'row',
                                    position: { vertical: 'bottom', horizontal: 'middle' },
                                    padding: 0,
                                },
                            }}
                        />
                    ) : (
                        <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                {localeMessages['no_data_yet'] || 'No data yet'}
                            </Typography>
                        </Box>
                    )}
                </Box>
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }} sx={{ display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ py: 3, borderRadius: { xs: 0, sm: 2 }, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)', flex: 1 }}>
                    <Typography variant="h6" align="center">{localeMessages['weekly_enrollments']}</Typography>
                    {isWeeklyStatsLoading ? (
                        <Box sx={{ px: 2 }}>
                            <Skeleton variant="rectangular" height={220} sx={{ borderRadius: 1, my: 2 }} />
                            <Skeleton variant="text" width="75%" sx={{ mx: 'auto' }} />
                        </Box>
                    ) : hasWeeklyChartData ? (
                        <BarChart
                            margin={{
                                top: 60,
                            }}
                            xAxis={[{ data: weeklyStats.map((stat) => stat.date) }]}
                            series={[{ data: weeklyStats.map((stat) => stat.count), color: theme.palette.secondary.main }]}
                            height={300}
                        />
                    ) : (
                        <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                {localeMessages['no_data_yet'] || 'No data yet'}
                            </Typography>
                        </Box>
                    )}
                </Box>
            </Grid>
        </Grid>
    );
}

export default CourseAnalyticsSection;
