import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Button, TextField, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Dialog, DialogTitle, DialogContent, DialogActions, Select, MenuItem, FormControl, InputLabel, Alert, Grid, Chip, IconButton } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';

export default function ToolManager({ user }) {
  const [tools, setTools] = useState([]);
  const [openRegister, setOpenRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState(null);

  // Registration Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [parametersStr, setParametersStr] = useState('{\n  "type": "object",\n  "properties": {},\n  "required": []\n}');
  const [toolType, setToolType] = useState('api');
  const [apiUrl, setApiUrl] = useState('');
  const [apiMethod, setApiMethod] = useState('GET');
  const [apiHeadersStr, setApiHeadersStr] = useState('{}');

  // Execution Test State
  const [selectedTool, setSelectedTool] = useState('');
  const [testParamsStr, setTestParamsStr] = useState('{}');
  const [testResult, setTestResult] = useState('');
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    if (!user) return;
    try {
      const res = await fetch(`/tool/?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setTools(data);
        if (data.length > 0 && !selectedTool) {
          setSelectedTool(data[0].name);
          // Set initial test arguments based on selected tool parameters
          setTestParamsStr(JSON.stringify(getSampleParams(data[0].parameters), null, 2));
        }
      }
    } catch (e) {
      console.error("Failed to load tools", e);
    }
  };

  const getSampleParams = (schema) => {
    const sample = {};
    if (schema && schema.properties) {
      Object.keys(schema.properties).forEach(key => {
        sample[key] = schema.properties[key].type === 'number' ? 0 : '';
      });
    }
    return sample;
  };

  const handleRegister = async () => {
    setAlert(null);
    let paramsObj, headersObj;
    
    try {
      paramsObj = JSON.parse(parametersStr);
    } catch (e) {
      setAlert({ type: 'error', message: 'Parameters field must be valid JSON schema' });
      return;
    }

    try {
      headersObj = JSON.parse(apiHeadersStr);
    } catch (e) {
      setAlert({ type: 'error', message: 'Headers field must be valid JSON' });
      return;
    }

    try {
      const res = await fetch('/tool/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim().replace(/\s+/g, '_'),
          description,
          parameters: paramsObj,
          type: toolType,
          url: apiUrl.trim() || null,
          method: apiMethod,
          headers: headersObj,
          user_id: user ? user.id : null
        })
      });
      
      if (res.ok) {
        setAlert({ type: 'success', message: `Tool '${name}' registered successfully!` });
        setName('');
        setDescription('');
        setParametersStr('{\n  "type": "object",\n  "properties": {},\n  "required": []\n}');
        setToolType('api');
        setApiUrl('');
        setApiMethod('GET');
        setApiHeadersStr('{}');
        setOpenRegister(false);
        fetchTools();
      } else {
        const err = await res.json();
        setAlert({ type: 'error', message: err.detail || 'Registration failed' });
      }
    } catch (e) {
      setAlert({ type: 'error', message: 'Network error during registration' });
    }
  };

  const handleDelete = async (toolName) => {
    try {
      const res = await fetch(`/tool/${toolName}`, { method: 'DELETE' });
      if (res.ok) {
        fetchTools();
      }
    } catch (e) {
      console.error("Failed to delete tool", e);
    }
  };

  const handleExecuteTest = async () => {
    setExecuting(true);
    setTestResult('');
    try {
      let params = {};
      try {
        params = JSON.parse(testParamsStr);
      } catch (e) {
        setTestResult("Error: Test parameters must be valid JSON");
        setExecuting(false);
        return;
      }

      const res = await fetch('/tool/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_name: selectedTool,
          parameters: params
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        setTestResult(data.result);
      } else {
        setTestResult(`Execution Error: ${data.detail || 'Failed to execute tool'}`);
      }
    } catch (e) {
      setTestResult(`Connection Error: ${e.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleToolSelect = (toolName) => {
    setSelectedTool(toolName);
    const tool = tools.find(t => t.name === toolName);
    if (tool) {
      setTestParamsStr(JSON.stringify(getSampleParams(tool.parameters), null, 2));
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, letterSpacing: '-0.02em' }}>
          Tool Registry & Execution
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenRegister(true)}>
          Register Tool
        </Button>
      </Box>

      {alert && (
        <Alert severity={alert.type} sx={{ mb: 3 }} onClose={() => setAlert(null)}>
          {alert.message}
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* Table List of Tools */}
        <Grid item xs={12} lg={8}>
          <TableContainer component={Paper} className="glass-panel">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tools.map((t) => (
                  <TableRow key={t.name} hover>
                    <TableCell sx={{ fontWeight: 500 }}><code>{t.name}</code></TableCell>
                    <TableCell>{t.description}</TableCell>
                    <TableCell>
                      <Chip 
                        size="small"
                        label={t.type.toUpperCase()} 
                        color={t.type === 'builtin' ? 'primary' : 'secondary'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {t.type === 'builtin' ? (
                        <Chip size="small" label="System" variant="filled" disabled />
                      ) : (
                        <IconButton size="small" color="error" onClick={() => handleDelete(t.name)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>

        {/* Execution Test Panel */}
        <Grid item xs={12} lg={4}>
          <Card className="glass-panel">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Test Tool Execution
              </Typography>
              
              <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                <InputLabel>Select Tool</InputLabel>
                <Select
                  value={selectedTool}
                  label="Select Tool"
                  onChange={(e) => handleToolSelect(e.target.value)}
                >
                  {tools.map(t => (
                    <MenuItem key={t.name} value={t.name}>{t.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                fullWidth
                multiline
                rows={4}
                label="Parameters (JSON Arguments)"
                value={testParamsStr}
                onChange={(e) => setTestParamsStr(e.target.value)}
                sx={{ mb: 2, '& textarea': { fontFamily: 'monospace', fontSize: '13px' } }}
              />

              <Button
                fullWidth
                variant="contained"
                color="success"
                startIcon={<PlayArrowIcon />}
                disabled={executing || !selectedTool}
                onClick={handleExecuteTest}
                sx={{ mb: 2 }}
              >
                {executing ? 'Executing...' : 'Run Test'}
              </Button>

              {testResult && (
                <Box>
                  <Typography variant="caption" display="block" sx={{ mb: 1, color: 'grey.500', fontWeight: 500 }}>
                    Execution Result:
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: '#020617', maxH: '200px', overflowY: 'auto' }}>
                    <Typography variant="body2" component="pre" sx={{ fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                      {testResult}
                    </Typography>
                  </Paper>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Register Tool Dialog */}
      <Dialog open={openRegister} onClose={() => setOpenRegister(false)} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 600 }}>Register Dynamic API Tool</DialogTitle>
        <DialogContent dividers>
          <TextField
            fullWidth
            margin="dense"
            label="Tool Name"
            placeholder="e.g. get_weather_forecast"
            value={name}
            onChange={(e) => setName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            margin="dense"
            label="Description (used by LLM semantic selection)"
            placeholder="e.g. Fetches weather details for a given city."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            multiline
            rows={5}
            margin="dense"
            label="Parameter JSON Schema (OpenAI Format)"
            value={parametersStr}
            onChange={(e) => setParametersStr(e.target.value)}
            sx={{ mb: 2, '& textarea': { fontFamily: 'monospace', fontSize: '13px' } }}
          />

          <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 2, mb: 1 }}>
            API Dynamic Calling Settings
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={8}>
              <TextField
                fullWidth
                margin="dense"
                label="API URL Endpoint"
                placeholder="e.g. https://api.api-provider.com/v1"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
              />
            </Grid>
            <Grid item xs={4}>
              <FormControl fullWidth margin="dense">
                <InputLabel>Method</InputLabel>
                <Select value={apiMethod} label="Method" onChange={(e) => setApiMethod(e.target.value)}>
                  <MenuItem value="GET">GET</MenuItem>
                  <MenuItem value="POST">POST</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
          <TextField
            fullWidth
            multiline
            rows={3}
            margin="dense"
            label="HTTP Request Headers (JSON object)"
            value={apiHeadersStr}
            onChange={(e) => setApiHeadersStr(e.target.value)}
            sx={{ mt: 2, '& textarea': { fontFamily: 'monospace', fontSize: '13px' } }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRegister(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleRegister}>Register</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
