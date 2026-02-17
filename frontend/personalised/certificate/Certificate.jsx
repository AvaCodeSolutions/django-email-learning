import render, { useAppContext } from "../../src/render";

import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import WorkspacePremiumIcon from '@mui/icons-material/WorkspacePremium';
import Grid from "@mui/material/Grid";
import { alpha } from "@mui/material/styles";
import { Alert } from "@mui/material";


const Certificate = () => {
    const { errorMessage } = useAppContext();
    return (<>{ errorMessage ? <Alert severity="error" sx={{ maxWidth: 800, margin: '20px auto' }}>
       {errorMessage}
    </Alert> : <CertificateContent /> }</>);
}

const CertificateContent = () => {
    const { localeMessages, name, issueDate, certificateNumber, qrcodeUrl, logoUrl } = useAppContext();

    return (
        <Box
            sx={{
                p: { xs: 1, sm: 2, md: 4 },
                width: '100%',
                boxSizing: 'border-box',
                display: 'flex',
                justifyContent: { xs: 'flex-start', md: 'center' },
                overflowX: 'auto',
                overflowY: 'hidden',
                WebkitOverflowScrolling: 'touch',
            }}
        >
            <Paper
                elevation={2}
                sx={(theme) => ({
                    flex: '0 0 auto',
                    padding: '10mm',
                    width: '277mm',
                    height: '190mm',
                    borderRadius: 3,
                    position: 'relative',
                    backgroundImage: (() => {
                        const band = alpha(theme.palette.secondary.main, 0.22);
                        const glow = alpha(theme.palette.primary.main, 0.35);
                        const baseStart = alpha(theme.palette.primary.main, 0.88);
                        const baseEnd = alpha(theme.palette.secondary.main, 0.88);
                        const hatch = alpha(theme.palette.common.white, 0.05);
                        return [
                            `linear-gradient(15deg, transparent 0 35%, ${band} 35% 41%, transparent 41% 100%)`,
                            `linear-gradient(-28deg, transparent 0 55%, ${band} 55% 61%, transparent 61% 100%)`,
                            `radial-gradient(circle at 10% 10%, ${glow} 0%, transparent 55%)`,
                            `radial-gradient(circle at 90% 90%, ${glow} 0%, transparent 55%)`,
                            `repeating-linear-gradient(45deg, ${hatch} 0 1px, transparent 1px 12px)`,
                            `repeating-linear-gradient(-45deg, ${hatch} 0 1px, transparent 1px 12px)`,
                            `linear-gradient(135deg, ${baseStart} 0%, ${baseEnd} 100%)`,
                        ].join(", ");
                    })(),
                    backgroundColor: alpha(theme.palette.common.white, 0.3),
                    backgroundBlendMode: 'screen, screen, soft-light, soft-light, overlay, overlay, normal',
                    overflow: 'hidden',
                    shadowColor: 'rgba(0, 0, 0, 0.5)',
                    // Optional: Force page breaks if you have multiple pages
                    pageBreakAfter: 'always',
                })}
            ><Paper
                elevation={0}
                sx={{
                    padding: "1mm",
                    borderRadius: 2,
                    boxSizing: 'border-box',
                    overflow: 'scroll',
                    width: '100%',
                    height: '100%',
                }}><Paper
                elevation={0}
                sx={(theme) => ({
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    borderRadius: 2,
                    border: `2px solid ${alpha(theme.palette.primary.main, 0.5)}`,
                    position: 'relative',
                    backgroundImage: (() => {
                        const fade = alpha(theme.palette.primary.main, 0.02);
                        return [
                            `repeating-linear-gradient(135deg, ${fade} 0 1px, transparent 2px 6px)`,
                        ].join(", ");
                    })(),
                    backgroundColor: alpha(theme.palette.common.white, 0.95),
                    boxShadow: `inset 0 0 0 1px ${alpha(theme.palette.common.black, 0.04)}`,
                    '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 16,
                        left: 16,
                        right: 16,
                        height: 6,
                        borderRadius: 999,
                        background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                        opacity: 0.25,
                    },
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 8,
                    boxSizing: 'border-box',
                })}
            >
                {/* Your content here */}
                <WorkspacePremiumIcon sx={(theme) => ({ fontSize: 86, color: theme.palette.secondary.main, mb: 2 })} />
                <Typography
                    variant="h1"
                    gutterBottom
                    sx={{
                        letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                    }}
                >
                    {localeMessages['title']}
                </Typography>
                <Typography
                    variant="h3"
                    align="center"
                    mt={4}
                    sx={{
                        fontWeight: 500,
                        maxWidth: '80%',
                    }}
                    dangerouslySetInnerHTML={{ __html: localeMessages['description'].replace(name, "<div style='font-size: 2em; padding: 0.5em; font-weight: 700;'>" + name + "</div>") }}
                >
                </Typography>
                <Grid container spacing={2} sx={{pt: 2, mt: 4, width: '100%', minHeight: '100px' }} alignItems="flex-end">
                    <Grid item size={4} sx={{ textAlign: 'center' }} >
                        <Typography variant="body2">
                            { logoUrl && <><img src={logoUrl} alt="Organization Logo" style={{ width: 80, height: 80, objectFit: 'contain' }} /><br /></> }
                            <b>{localeMessages['organization_team']}</b><br />
                            {localeMessages['issue_date']}: {issueDate}
                        </Typography>
                    </Grid>
                    <Grid item size={4} sx={{ textAlign: 'center' }} >
                    </Grid>
                    <Grid item size={4} sx={{ textAlign: 'center' }} >
                        <Typography variant="body2">
                            <img src={qrcodeUrl} alt="QR Code" style={{ width: 80, height: 80 }} />
                            <br />
                            {localeMessages['certificate_number']}:<br />{certificateNumber}
                        </Typography>
                    </Grid>
                </Grid>
            </Paper>
            </Paper>
        </Paper>
        </Box>
    )
}


render({children: <Certificate />});
