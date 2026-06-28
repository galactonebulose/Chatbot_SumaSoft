import React, { useState } from 'react';
import { Box, Card, CardContent, Typography, TextField, Button, Alert, CircularProgress, Link } from '@mui/material';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import PersonAddOutlinedIcon from '@mui/icons-material/PersonAddOutlined';

export default function LoginPanel({ onLoginSuccess }) {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [alertInfo, setAlertInfo] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setAlertInfo({ type: 'error', message: 'Please enter both username and password.' });
      return;
    }
    if (isRegisterMode && !email.trim()) {
      setAlertInfo({ type: 'error', message: 'Please enter a valid email address.' });
      return;
    }

    setLoading(true);
    setAlertInfo(null);

    const url = isRegisterMode ? '/user/register' : '/user/login';
    const payload = isRegisterMode
      ? { username, email, password, full_name: fullName || null }
      : { username, password };

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        if (isRegisterMode) {
          setAlertInfo({ type: 'success', message: 'Registration successful! You can now log in.' });
          setIsRegisterMode(false);
          setPassword('');
        } else {
          // Success login
          onLoginSuccess(data);
        }
      } else {
        setAlertInfo({ type: 'error', message: data.detail || 'Authentication failed.' });
      }
    } catch (err) {
      setAlertInfo({ type: 'error', message: 'Connection error. Make sure the backend server is running.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      width: '100vw',
      background: 'radial-gradient(circle at top right, rgba(99, 102, 241, 0.15), transparent), radial-gradient(circle at bottom left, rgba(236, 72, 153, 0.1), transparent), #070a13',
      p: 2
    }}>
      <Card className="glass-panel" sx={{
        width: '100%',
        maxWidth: 420,
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(15, 23, 42, 0.45)',
        backdropFilter: 'blur(10px)',
        borderRadius: 4
      }}>
        <CardContent sx={{ p: 4 }}>
          {/* Header Icon */}
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
            <Box sx={{
              p: 2,
              borderRadius: '50%',
              background: 'linear-gradient(to right, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              {isRegisterMode ? (
                <PersonAddOutlinedIcon sx={{ fontSize: 32, color: '#ec4899' }} />
              ) : (
                <LockOutlinedIcon sx={{ fontSize: 32, color: '#818cf8' }} />
              )}
            </Box>
          </Box>

          <Typography variant="h5" align="center" gutterBottom sx={{ fontWeight: 700, letterSpacing: '-0.02em' }}>
            {isRegisterMode ? 'Create an Account' : 'Welcome Back'}
          </Typography>
          <Typography variant="body2" align="center" sx={{ color: 'grey.500', mb: 3 }}>
            {isRegisterMode
              ? 'Register to configure resources, custom tools, and map your chats.'
              : 'Enter your credentials to access your personal workspace.'}
          </Typography>

          {alertInfo && (
            <Alert severity={alertInfo.type} sx={{ mb: 3 }} onClose={() => setAlertInfo(null)}>
              {alertInfo.message}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <TextField
                fullWidth
                label="Username"
                variant="outlined"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                required
              />

              {isRegisterMode && (
                <>
                  <TextField
                    fullWidth
                    label="Email Address"
                    type="email"
                    variant="outlined"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={loading}
                    required
                  />
                  <TextField
                    fullWidth
                    label="Full Name (Optional)"
                    variant="outlined"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    disabled={loading}
                  />
                </>
              )}

              <TextField
                fullWidth
                label="Password"
                type="password"
                variant="outlined"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />

              <Button
                type="submit"
                variant="contained"
                size="large"
                fullWidth
                disabled={loading}
                sx={{
                  mt: 1,
                  py: 1.5,
                  fontWeight: 600,
                  fontSize: '15px',
                  background: isRegisterMode
                    ? 'linear-gradient(to right, #ec4899, #be185d)'
                    : 'linear-gradient(to right, #6366f1, #4f46e5)',
                  '&:hover': {
                    background: isRegisterMode
                      ? 'linear-gradient(to right, #db2777, #9d174d)'
                      : 'linear-gradient(to right, #4f46e5, #3730a3)'
                  }
                }}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : (isRegisterMode ? 'Register Now' : 'Sign In')}
              </Button>
            </Box>
          </form>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Link
              component="button"
              variant="body2"
              onClick={() => {
                setIsRegisterMode(!isRegisterMode);
                setAlertInfo(null);
                setUsername('');
                setEmail('');
                setPassword('');
                setFullName('');
              }}
              sx={{
                color: 'primary.light',
                textDecoration: 'none',
                fontWeight: 500,
                cursor: 'pointer',
                '&:hover': { textDecoration: 'underline' }
              }}
            >
              {isRegisterMode ? 'Already have an account? Sign In' : "Don't have an account? Register"}
            </Link>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
