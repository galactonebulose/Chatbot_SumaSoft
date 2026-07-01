import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, TextField, Button, Alert, Grid, InputAdornment } from '@mui/material';
import KeyIcon from '@mui/icons-material/VpnKey';
import SaveIcon from '@mui/icons-material/Save';

export default function SettingsPanel() {
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [configState, setConfigState] = useState({ has_openai_key: false, has_anthropic_key: false, has_gemini_key: false });
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/v1/llm/config');
      if (res.ok) {
        const data = await res.json();
        setConfigState(data);
      }
    } catch (e) {
      console.error("Failed to load config", e);
    }
  };

  const handleSave = async (provider, key) => {
    if (!key.trim()) {
      setAlert({ type: 'error', message: 'API key cannot be empty' });
      return;
    }
    
    setLoading(true);
    setAlert(null);
    try {
      const res = await fetch('/api/v1/llm/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: key.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        const providerNameMap = {
          openai: 'OpenAI',
          anthropic: 'Anthropic',
          gemini: 'Google Gemini'
        };
        setAlert({ type: 'success', message: `${providerNameMap[provider]} API key saved successfully!` });
        if (provider === 'openai') setOpenaiKey('');
        if (provider === 'anthropic') setAnthropicKey('');
        if (provider === 'gemini') setGeminiKey('');
        fetchConfig();
      } else {
        setAlert({ type: 'error', message: data.detail || 'Failed to save configuration' });
      }
    } catch (e) {
      setAlert({ type: 'error', message: 'Network error saving configuration' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 4, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, letterSpacing: '-0.02em', mb: 3 }}>
        LLM Configuration
      </Typography>

      {alert && (
        <Alert severity={alert.type} sx={{ mb: 3 }} onClose={() => setAlert(null)}>
          {alert.message}
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* OpenAI Card */}
        <Grid item xs={12} md={4}>
          <Card className="glass-panel" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                OpenAI (ChatGPT)
              </Typography>
              <Typography variant="body2" sx={{ color: 'grey.400', mb: 3 }}>
                Configure OpenAI models (like gpt-4o, gpt-4o-mini).
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" display="block" sx={{ color: configState.has_openai_key ? 'success.main' : 'warning.main', mb: 1, fontWeight: 500 }}>
                  ● {configState.has_openai_key ? 'API Key Active (Configured)' : 'API Key Not Set'}
                </Typography>
                <TextField
                  fullWidth
                  type="password"
                  label="OpenAI API Key"
                  placeholder="sk-proj-..."
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <KeyIcon sx={{ color: 'grey.500' }} />
                      </InputAdornment>
                    ),
                  }}
                  variant="outlined"
                  size="small"
                />
              </Box>
              
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                disabled={loading}
                onClick={() => handleSave('openai', openaiKey)}
                sx={{ textTransform: 'none' }}
              >
                Save OpenAI Key
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Anthropic Card */}
        <Grid item xs={12} md={4}>
          <Card className="glass-panel" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Anthropic (Claude)
              </Typography>
              <Typography variant="body2" sx={{ color: 'grey.400', mb: 3 }}>
                Configure Anthropic Claude models (like claude-3-5-sonnet).
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" display="block" sx={{ color: configState.has_anthropic_key ? 'success.main' : 'warning.main', mb: 1, fontWeight: 500 }}>
                  ● {configState.has_anthropic_key ? 'API Key Active (Configured)' : 'API Key Not Set'}
                </Typography>
                <TextField
                  fullWidth
                  type="password"
                  label="Anthropic API Key"
                  placeholder="sk-ant-..."
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <KeyIcon sx={{ color: 'grey.500' }} />
                      </InputAdornment>
                    ),
                  }}
                  variant="outlined"
                  size="small"
                />
              </Box>
              
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                disabled={loading}
                onClick={() => handleSave('anthropic', anthropicKey)}
                sx={{ textTransform: 'none' }}
              >
                Save Anthropic Key
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Google Gemini Card */}
        <Grid item xs={12} md={4}>
          <Card className="glass-panel" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Google Gemini
              </Typography>
              <Typography variant="body2" sx={{ color: 'grey.400', mb: 3 }}>
                Configure Google Gemini models (like gemini-3.5-flash).
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" display="block" sx={{ color: configState.has_gemini_key ? 'success.main' : 'warning.main', mb: 1, fontWeight: 500 }}>
                  ● {configState.has_gemini_key ? 'API Key Active (Configured)' : 'API Key Not Set'}
                </Typography>
                <TextField
                  fullWidth
                  type="password"
                  label="Gemini API Key"
                  placeholder="AIzaSy..."
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <KeyIcon sx={{ color: 'grey.500' }} />
                      </InputAdornment>
                    ),
                  }}
                  variant="outlined"
                  size="small"
                />
              </Box>
              
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                disabled={loading}
                onClick={() => handleSave('gemini', geminiKey)}
                sx={{ textTransform: 'none' }}
              >
                Save Gemini Key
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
