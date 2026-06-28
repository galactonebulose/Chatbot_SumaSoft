import React, { useState } from 'react';
import { Box, Card, CardContent, Typography, TextField, Button, Grid, Select, MenuItem, FormControl, InputLabel, Paper, Alert, LinearProgress, Divider } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SyncIcon from '@mui/icons-material/Sync';
import SearchIcon from '@mui/icons-material/Search';

export default function KnowledgeHub({ user }) {
  // File Upload State
  const [uploading, setUploading] = useState(false);
  const [uploadAlert, setUploadAlert] = useState(null);

  // Connector State
  const [connectorType, setConnectorType] = useState('directory');
  const [syncing, setSyncing] = useState(false);
  const [syncAlert, setSyncAlert] = useState(null);
  
  // Dynamic fields configs
  const [dirPath, setDirPath] = useState('');
  const [mongoUrl, setMongoUrl] = useState('mongodb://localhost:27017');
  const [mongoDb, setMongoDb] = useState('chatbot');
  const [mongoCol, setMongoCol] = useState('documents');
  const [mongoFields, setMongoFields] = useState('title, content');
  
  const [pgUrl, setPgUrl] = useState('postgresql://user:pass@localhost:5432/chatbot');
  const [pgTable, setPgTable] = useState('documents');
  const [pgColumns, setPgColumns] = useState('title, description');
  
  const [apiUrl, setApiUrl] = useState('https://jsonplaceholder.typicode.com/posts');
  const [apiMethod, setApiMethod] = useState('GET');
  const [apiHeaders, setApiHeaders] = useState('{}');
  const [apiFieldsPath, setApiFieldsPath] = useState('');

  // Semantic Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);

  // Ingest/Upload File
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadAlert(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`/resource/upload?user_id=${user ? user.id : ''}`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      if (res.ok) {
        setUploadAlert({
          type: 'success',
          message: `Successfully uploaded '${data.filename}'. Indexed ${data.chunks_indexed} document fragments into Qdrant.`
        });
      } else {
        setUploadAlert({ type: 'error', message: data.detail || 'Upload failed' });
      }
    } catch (e) {
      setUploadAlert({ type: 'error', message: 'Connection error during upload' });
    } finally {
      setUploading(false);
    }
  };

  // Sync Data Connector
  const handleSyncConnector = async () => {
    setSyncing(true);
    setSyncAlert(null);
    
    let config = {};
    if (connectorType === 'directory') {
      config = { path: dirPath };
    } else if (connectorType === 'mongodb') {
      config = {
        mongo_url: mongoUrl,
        db_name: mongoDb,
        collection_name: mongoCol,
        fields: mongoFields.split(',').map(f => f.trim())
      };
    } else if (connectorType === 'postgresql') {
      config = {
        postgres_url: pgUrl,
        table_name: pgTable,
        columns: pgColumns.split(',').map(c => c.trim())
      };
    } else if (connectorType === 'api') {
      let headersObj = {};
      try {
        headersObj = JSON.parse(apiHeaders);
      } catch (e) {
        setSyncAlert({ type: 'error', message: 'API Headers config must be valid JSON' });
        setSyncing(false);
        return;
      }
      config = {
        url: apiUrl,
        method: apiMethod,
        headers: headersObj,
        fields_path: apiFieldsPath || null
      };
    }

    try {
      const res = await fetch('/resource/connector/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: connectorType,
          config,
          user_id: user ? user.id : null
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        setSyncAlert({
          type: 'success',
          message: `Sync successful! ${data.files_processed || data.documents_processed || data.rows_processed || data.records_processed || 0} entities processed. Indexed ${data.total_chunks || 0} chunks.`
        });
      } else {
        setSyncAlert({ type: 'error', message: data.detail || 'Connector Sync failed' });
      }
    } catch (e) {
      setSyncAlert({ type: 'error', message: `Sync failed: ${e.message}` });
    } finally {
      setSyncing(false);
    }
  };

  // Search Knowledge Base
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch('/resource/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, top_k: 3 })
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (e) {
      console.error("Semantic search failed", e);
    } finally {
      setSearching(false);
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, letterSpacing: '-0.02em', mb: 3 }}>
        Knowledge Management & RAG
      </Typography>

      <Grid container spacing={4}>
        {/* Document Ingestion Panel */}
        <Grid item xs={12} md={6}>
          <Card className="glass-panel" sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Resource Ingestion File Uploader
              </Typography>
              <Typography variant="body2" sx={{ color: 'grey.400', mb: 3 }}>
                Upload PDF, DOCX, CSV, or TXT documents directly. The file will be parsed, chunked, embedded, and indexed inside your vector database.
              </Typography>

              {uploadAlert && (
                <Alert severity={uploadAlert.type} sx={{ mb: 2 }} onClose={() => setUploadAlert(null)}>
                  {uploadAlert.message}
                </Alert>
              )}

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', p: 3, border: '2px dashed rgba(255,255,255,0.1)', borderRadius: 2, bgcolor: 'rgba(255,255,255,0.01)', mb: 2 }}>
                <CloudUploadIcon sx={{ fontSize: 48, color: 'grey.500', mb: 2 }} />
                <Button
                  component="label"
                  variant="outlined"
                  disabled={uploading}
                  sx={{ textTransform: 'none' }}
                >
                  {uploading ? 'Processing File...' : 'Choose File'}
                  <input type="file" hidden accept=".pdf,.docx,.csv,.txt" onChange={handleFileUpload} />
                </Button>
                <Typography variant="caption" sx={{ mt: 1, color: 'grey.500' }}>
                  Supported formats: PDF, DOCX, TXT, CSV (max 10MB)
                </Typography>
              </Box>
              {uploading && <LinearProgress color="primary" sx={{ borderRadius: 1 }} />}
            </CardContent>
          </Card>

          {/* Connectors Panel
          <Card className="glass-panel">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Structured Data Connectors
              </Typography>
              <Typography variant="body2" sx={{ color: 'grey.400', mb: 3 }}>
                Configure and synchronize folders, relational/document databases, or external JSON APIs directly to the chatbot's vector workspace.
              </Typography>

              {syncAlert && (
                <Alert severity={syncAlert.type} sx={{ mb: 2 }} onClose={() => setSyncAlert(null)}>
                  {syncAlert.message}
                </Alert>
              )}

              <FormControl fullWidth size="small" sx={{ mb: 3 }}>
                <InputLabel>Connector Type</InputLabel>
                <Select
                  value={connectorType}
                  label="Connector Type"
                  onChange={(e) => {
                    setConnectorType(e.target.value);
                    setSyncAlert(null);
                  }}
                >
                  <MenuItem value="directory">Local Directory Folder</MenuItem>
                  <MenuItem value="mongodb">MongoDB Collection</MenuItem>
                  <MenuItem value="postgresql">PostgreSQL Database</MenuItem>
                  <MenuItem value="api">Web API Endpoint</MenuItem>
                </Select>
              </FormControl>

              {connectorType === 'directory' && (
                <TextField
                  fullWidth
                  size="small"
                  label="Local Absolute Path to Folder"
                  placeholder="e.g. C:\SDriveStuff\Internship\data"
                  value={dirPath}
                  onChange={(e) => setDirPath(e.target.value)}
                  sx={{ mb: 3 }}
                />
              )}

              {connectorType === 'mongodb' && (
                <Box>
                  <TextField fullWidth size="small" label="MongoDB Connection URL" value={mongoUrl} onChange={(e) => setMongoUrl(e.target.value)} sx={{ mb: 2 }} />
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <TextField fullWidth size="small" label="Database Name" value={mongoDb} onChange={(e) => setMongoDb(e.target.value)} />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField fullWidth size="small" label="Collection Name" value={mongoCol} onChange={(e) => setMongoCol(e.target.value)} />
                    </Grid>
                  </Grid>
                  <TextField fullWidth size="small" label="Fields to Ingest (comma separated)" value={mongoFields} onChange={(e) => setMongoFields(e.target.value)} sx={{ mb: 3 }} />
                </Box>
              )}

              {connectorType === 'postgresql' && (
                <Box>
                  <TextField fullWidth size="small" label="PostgreSQL Connection URL" value={pgUrl} onChange={(e) => setPgUrl(e.target.value)} sx={{ mb: 2 }} />
                  <TextField fullWidth size="small" label="Target Table Name" value={pgTable} onChange={(e) => setPgTable(e.target.value)} sx={{ mb: 2 }} />
                  <TextField fullWidth size="small" label="Columns to Ingest (comma separated)" value={pgColumns} onChange={(e) => setPgColumns(e.target.value)} sx={{ mb: 3 }} />
                </Box>
              )}

              {connectorType === 'api' && (
                <Box>
                  <TextField fullWidth size="small" label="HTTP URL Endpoint" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} sx={{ mb: 2 }} />
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Method</InputLabel>
                        <Select value={apiMethod} label="Method" onChange={(e) => setApiMethod(e.target.value)}>
                          <MenuItem value="GET">GET</MenuItem>
                          <MenuItem value="POST">POST</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={6}>
                      <TextField fullWidth size="small" label="JSON List Path (optional)" placeholder="e.g. data.items" value={apiFieldsPath} onChange={(e) => setApiFieldsPath(e.target.value)} />
                    </Grid>
                  </Grid>
                  <TextField fullWidth multiline rows={2} size="small" label="HTTP Headers (JSON)" value={apiHeaders} onChange={(e) => setApiHeaders(e.target.value)} sx={{ mb: 3, '& textarea': { fontFamily: 'monospace', fontSize: '13px' } }} />
                </Box>
              )}

              <Button
                fullWidth
                variant="contained"
                startIcon={<SyncIcon />}
                disabled={syncing}
                onClick={handleSyncConnector}
                sx={{ textTransform: 'none' }}
              >
                {syncing ? 'Synchronizing Ingestion...' : 'Sync Connector Now'}
              </Button>
            </CardContent>
          </Card>
          */}
        </Grid>

        {/* Semantic Qdrant Search sandbox */}
        <Grid item xs={12} md={6}>
          <Card className="glass-panel" sx={{ height: '100%' }}>
            <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Qdrant Semantic Search Sandbox
              </Typography>
              <Typography variant="body2" sx={{ color: 'grey.400', mb: 3 }}>
                Verify if your documents and connector data have been indexed correctly by executing direct query vectors against Qdrant.
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
                <TextField
                  fullWidth
                  size="small"
                  label="Search prompt query..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => { if (e.key === 'Enter') handleSearch(); }}
                />
                <Button variant="contained" color="primary" disabled={searching} onClick={handleSearch} sx={{ minWidth: '100px' }}>
                  {searching ? 'Searching...' : <SearchIcon />}
                </Button>
              </Box>

              <Divider sx={{ mb: 3 }} />

              <Box sx={{ flexGrow: 1, overflowY: 'auto', maxH: '500px' }}>
                {searchResults.length === 0 ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px', border: '1px dashed rgba(255,255,255,0.05)', borderRadius: 2 }}>
                    <Typography variant="body2" sx={{ color: 'grey.500' }}>
                      No search results yet. Type a query above to query index.
                    </Typography>
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {searchResults.map((r, idx) => (
                      <Paper key={idx} variant="outlined" sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.01)', borderColor: 'rgba(255,255,255,0.05)' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.main' }}>
                            Source: {r.metadata.filename || r.metadata.table_name || r.metadata.api_url || 'Dynamic Ingestion'}
                          </Typography>
                          <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 600 }}>
                            Score: {r.score.toFixed(4)}
                          </Typography>
                        </Box>
                        <Typography variant="body2" sx={{ color: 'grey.300', fontSize: '13.5px', lineHeight: 1.5 }}>
                          {r.text}
                        </Typography>
                      </Paper>
                    ))}
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
