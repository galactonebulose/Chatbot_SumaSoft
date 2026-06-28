import React, { useState } from 'react';
import { Box, ThemeProvider, createTheme, CssBaseline } from '@mui/material';

import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import ToolManager from './components/ToolManager';
import KnowledgeHub from './components/KnowledgeHub';
import SettingsPanel from './components/SettingsPanel';
import LoginPanel from './components/LoginPanel';

// Customize our custom premium Dark Theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#6366f1', // Indigo
      dark: '#4f46e5',
      light: '#818cf8',
    },
    secondary: {
      main: '#ec4899', // Pink
    },
    background: {
      default: '#070a13',
      paper: 'rgba(15, 23, 42, 0.55)', // glassmorphic paper background
    },
    text: {
      primary: '#f1f5f9',
      secondary: '#94a3b8',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '10px',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: '10px',
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          borderRadius: '10px',
        },
      },
    },
  },
});

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatPanel user={user} />;
      case 'tools':
        return <ToolManager user={user} />;
      case 'knowledge':
        return <KnowledgeHub user={user} />;
      case 'settings':
        return <SettingsPanel user={user} onLogout={handleLogout} />;
      default:
        return <ChatPanel user={user} />;
    }
  };

  if (!user) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LoginPanel onLoginSuccess={handleLoginSuccess} />
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
        {/* Navigation Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} user={user} onLogout={handleLogout} />
        
        {/* Main Content Workspace */}
        <Box sx={{ flexGrow: 1, height: '100vh', overflowY: 'auto', bgcolor: 'transparent' }}>
          {renderContent()}
        </Box>
      </Box>
    </ThemeProvider>
  );
}
