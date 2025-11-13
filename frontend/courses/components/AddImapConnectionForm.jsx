
import { useState, useMemo, useEffect } from 'react';
import { Accordion, AccordionDetails, AccordionSummary, Box, FormControl, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlusIcon from '@mui/icons-material/Add';
import CreateImapForm from './CreateImapForm';

function AddImapConnectionForm({onChangeCallback, activeOrganizationId, initialImapConnectionId = null}) {
  const [imapConnections, setImapConnections] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [imapConnectionId, setImapConnectionId] = useState(initialImapConnectionId);

  const switchExpanded = () => {
    if (hasImapConnection) {
      setExpanded(!expanded);
    }
  };

  const apiBaseUrl = localStorage.getItem('apiBaseUrl');

  const hasImapConnection = useMemo(() => {
    let returnValue = imapConnections.length > 0;
    return returnValue;
  }, [imapConnections]);

  const handleImapConnectionChange = (newId) => {
    setImapConnectionId(newId);
    if (onChangeCallback) {
      onChangeCallback(newId);
    }
  };

  useEffect(() => {
    fetch(apiBaseUrl + '/organizations/' + activeOrganizationId + '/imap-connections/', {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then((response) => response.json())
      .then((data) => {
        setImapConnections(data.imap_connections);
        if (data.imap_connections.length == 0) {
          setExpanded(true);
        }
      })
      .catch((error) => {
        console.error('Error fetching IMAP connections:', error);
      });
  }, []);

  return (
    <div>
      { hasImapConnection && (
        <FormControl sx={{ marginBottom: '16px', minWidth: '100%' }}>
          <InputLabel id="demo-simple-select-helper-label">IMAP Connection</InputLabel>
          <Select
            labelId="demo-simple-select-helper-label"
            id="demo-simple-select-helper"
            label="IMAP Connection"
            value={imapConnectionId || ''}
            onChange={(event) => handleImapConnectionChange(event.target.value)}
          >
            <MenuItem value={null}>None</MenuItem>
            {imapConnections.map((connection) => (
              <MenuItem key={connection.id} value={connection.id} style={{ fontWeight: connection.id === imapConnectionId ? 'bold' : 'normal' }}>
                {connection.email}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      <Accordion expanded={expanded} onChange={switchExpanded}>
        <AccordionSummary
          expandIcon={hasImapConnection ? <ExpandMoreIcon /> : null}
          aria-controls="panel1-content"
          id="panel1-header"
        ><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PlusIcon /><Typography component="span">New IMAP connection</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <CreateImapForm onSuccess={(newConnection) => {
            const updatedConnections = [...imapConnections, newConnection];
            setImapConnections(updatedConnections);
            setImapConnectionId(newConnection.id);
            if (onChangeCallback) {
              onChangeCallback(newConnection.id);
            }
            setExpanded(false);
          }} activeOrganizationId={activeOrganizationId} />
        </AccordionDetails>
      </Accordion>
    </div>
  );
}

export default AddImapConnectionForm;
