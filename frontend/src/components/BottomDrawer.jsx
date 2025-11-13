import 'vite/modulepreload-polyfill'
import { Fab, Drawer, Box } from "@mui/material";
import { useState } from "react";

function BottomDrawer({icon, children}) {
    const [drawerOpen, setDrawerOpen] = useState(false);
    const toggleDrawer = (newOpen) => () => {
        setDrawerOpen(newOpen);
    };
    return (
        <>
            <Fab size="small" color="secondary" aria-label="Filter list" sx={{ position: 'fixed', bottom: 16, right: 16, display: {md: "none"}, boxShadow: "1px 1px 5px rgba(0, 0, 0, 0.2)" }} onClick={toggleDrawer(true)}>
                {icon}
            </Fab>
            <Drawer open={drawerOpen} onClose={toggleDrawer(false)} display={{md: "none" }} anchor='bottom'
                slotProps={{ backdrop: { sx: { backgroundColor: 'rgba(251, 251, 255, 0.01)' }}, paper: { sx: { boxShadow: '2px 0px 8px rgba(0, 0, 0, 0.1)'}}}}>
                <Box p={2}>
                {children}
                </Box>
            </Drawer>
        </>
    );
}

export default BottomDrawer;
