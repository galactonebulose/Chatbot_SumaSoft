import React from 'react';
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography, Divider, Avatar, IconButton } from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import BuildIcon from '@mui/icons-material/Build';
import StorageIcon from '@mui/icons-material/Storage';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';

export default function Sidebar({ activeTab, setActiveTab, user, onLogout }) {
  const menuItems = [
    { id: 'chat', label: 'Chat Workspace', icon: <ChatIcon /> },
    { id: 'tools', label: 'Tool Registry', icon: <BuildIcon /> },
    { id: 'knowledge', label: 'Knowledge Hub', icon: <StorageIcon /> },
    { id: 'settings', label: 'Settings', icon: <SettingsIcon /> },
  ];

  return (
    <Box sx={{
      width: 260,
      height: '100vh',
      borderRight: '1px solid rgba(255, 255, 255, 0.08)',
      display: 'flex',
      flexDirection: 'column',
      background: 'rgba(15, 23, 42, 0.4)',
    }}>
      {/* Brand Title */}
      <Box sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Typography variant="h5" sx={{
          fontWeight: 700,
          background: 'linear-gradient(to right, #818cf8, #6366f1)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          letterSpacing: '-0.03em'
        }}>
          🤖 Chatbot Admin
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.06)' }} />

      {/* Nav List */}
      <List sx={{ flexGrow: 1, px: 2, py: 3, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {menuItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <ListItemButton
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              sx={{
                borderRadius: 2,
                py: 1.5,
                px: 2,
                bgcolor: isActive ? 'rgba(99, 102, 241, 0.08)' : 'transparent',
                border: isActive ? '1px solid rgba(99, 102, 241, 0.2)' : '1px solid transparent',
                color: isActive ? '#818cf8' : 'grey.400',
                '&:hover': {
                  bgcolor: isActive ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  color: isActive ? '#818cf8' : '#fff',
                },
                transition: 'all 0.2s ease',
              }}
            >
              <ListItemIcon sx={{
                color: isActive ? '#818cf8' : 'grey.500',
                minWidth: 40,
                transition: 'color 0.2s ease',
              }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText 
                primary={item.label} 
                primaryTypographyProps={{
                  fontSize: '14.5px',
                  fontWeight: isActive ? 600 : 500,
                  letterSpacing: '-0.01em'
                }} 
              />
            </ListItemButton>
          );
        })}
      </List>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.06)' }} />

      {/* User profile section */}
      {user && (
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, overflow: 'hidden' }}>
            <Avatar sx={{
              bgcolor: 'primary.main',
              fontWeight: 600,
              fontSize: '13px',
              width: 32,
              height: 32
            }}>
              {user.username ? user.username.substring(0, 2).toUpperCase() : 'U'}
            </Avatar>
            <Box sx={{ overflow: 'hidden' }}>
              <Typography variant="body2" noWrap sx={{ fontWeight: 600, fontSize: '13px', lineHeight: 1.2 }}>
                {user.full_name || user.username}
              </Typography>
              <Typography variant="caption" noWrap sx={{ color: 'grey.500', display: 'block', fontSize: '10.5px' }}>
                {user.email}
              </Typography>
            </Box>
          </Box>
          <IconButton size="small" onClick={onLogout} sx={{ color: 'grey.500', '&:hover': { color: 'error.main' } }}>
            <LogoutIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Box>
      )}

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.06)' }} />

      {/* Footer Info */}
      <Box sx={{ p: 2.5, pt: 1.5 }}>
        <Typography variant="caption" sx={{ color: 'grey.600', fontWeight: 500 }}>
          SumaSoft Internship Project
        </Typography>
      </Box>
    </Box>
  );
}
