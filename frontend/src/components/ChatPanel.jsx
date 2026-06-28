import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, Typography, TextField, Button, Select, MenuItem, FormControl, InputLabel, CircularProgress, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, Rating } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import SettingsIcon from '@mui/icons-material/Settings';
import CodeIcon from '@mui/icons-material/Code';

export default function ChatPanel({ user }) {
  const [provider, setProvider] = useState('ollama');
  const [model, setModel] = useState('llama3.2:3b');
  const [modelsList, setModelsList] = useState({
    ollama: ['llama3.2:3b', 'llama3.2', 'llama3.1'],
    openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
    anthropic: ['claude-3-5-sonnet-latest', 'claude-3-haiku-20240307']
  });

  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState('');
  const [sessions, setSessions] = useState([]);
  const [wsStatus, setWsStatus] = useState('Disconnected');
  const [thinking, setThinking] = useState(false);

  // Feedback Dialog State
  const [openFeedback, setOpenFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState('');

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchLLMInfo();
    fetchSessions();
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    // Scroll to bottom whenever messages or thinking state changes
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, thinking]);

  const fetchSessions = async () => {
    if (!user) return;
    try {
      const res = await fetch(`/chat/sessions?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (e) {
      console.error("Failed to load sessions list", e);
    }
  };

  const handleSelectSession = async (sId) => {
    try {
      setThinking(true);
      const res = await fetch(`/chat/sessions/${sId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
        setSessionId(sId);
        
        // Match selection UI dropdowns
        const sessMeta = sessions.find(s => s.id === sId);
        if (sessMeta) {
          if (sessMeta.provider) setProvider(sessMeta.provider);
          if (sessMeta.model) setModel(sessMeta.model);
        }
      }
    } catch (e) {
      console.error("Failed to load session history", e);
    } finally {
      setThinking(false);
    }
  };

  const handleDeleteSession = async (sId) => {
    try {
      const res = await fetch(`/chat/sessions/${sId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        if (sessionId === sId) {
          handleNewChat();
        }
        fetchSessions();
      }
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };

  const handleNewChat = () => {
    setSessionId('');
    setMessages([]);
  };

  const fetchLLMInfo = async () => {
    try {
      const res = await fetch('/api/v1/llm/models');
      if (res.ok) {
        const data = await res.json();
        if (data.models) {
          setModelsList(data.models);
          // Set defaults if available
          if (data.default_provider) {
            setProvider(data.default_provider);
            const models = data.models[data.default_provider] || [];
            if (models.length > 0) setModel(models[0]);
          }
        }
      }
    } catch (e) {
      console.error("Failed to load models list", e);
    }
  };

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    // Connect to Vite server socket proxy or direct API
    const wsUrl = `${protocol}//${host}/chat/ws`;
    
    setWsStatus('Connecting...');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('Connected');
    };

    ws.onclose = () => {
      setWsStatus('Disconnected - Reconnecting...');
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
      setWsStatus('Connection Error');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'session_created') {
        setSessionId(data.session_id);
        fetchSessions();
      }
      else if (data.type === 'thinking') {
        setThinking(true);
      }
      else if (data.type === 'token') {
        setThinking(false);
        setMessages((prev) => {
          const list = [...prev];
          if (list.length === 0 || list[list.length - 1].sender !== 'bot') {
            list.push({ sender: 'bot', text: data.content, toolRuns: [] });
          } else {
            list[list.length - 1].text += data.content;
          }
          return list;
        });
      }
      else if (data.type === 'tool_call') {
        setThinking(false);
        setMessages((prev) => {
          const list = [...prev];
          const newTool = {
            name: data.tool_name,
            params: data.parameters,
            result: '',
            status: 'running'
          };
          if (list.length === 0 || list[list.length - 1].sender !== 'bot') {
            list.push({ sender: 'bot', text: '', toolRuns: [newTool] });
          } else {
            list[list.length - 1].toolRuns.push(newTool);
          }
          return list;
        });
      }
      else if (data.type === 'tool_result') {
        setMessages((prev) => {
          const list = [...prev];
          if (list.length > 0 && list[list.length - 1].sender === 'bot') {
            const botMsg = list[list.length - 1];
            const activeTool = botMsg.toolRuns.find(tr => tr.name === data.tool_name && tr.status === 'running');
            if (activeTool) {
              activeTool.result = data.result;
              activeTool.status = 'complete';
            }
          }
          return list;
        });
      }
      else if (data.type === 'complete') {
        setThinking(false);
        setMessages((prev) => {
          const list = [...prev];
          if (list.length > 0 && list[list.length - 1].sender === 'bot') {
            list[list.length - 1].text = data.content;
          }
          return list;
        });
        if (data.session_id) {
          setSessionId(data.session_id);
          fetchSessions();
        }
      }
      else if (data.type === 'error') {
        setThinking(false);
        setMessages((prev) => [...prev, { sender: 'error', text: `❌ Error: ${data.content}`, toolRuns: [] }]);
      }
    };
  };

  const handleSend = () => {
    if (!message.trim()) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = {
        message: message.trim(),
        provider,
        model,
        session_id: sessionId || null,
        user_id: user ? user.id : null
      };
      
      setMessages((prev) => [...prev, { sender: 'user', text: message.trim(), toolRuns: [] }]);
      wsRef.current.send(JSON.stringify(payload));
      setMessage('');
    } else {
      setMessages((prev) => [...prev, { sender: 'error', text: '❌ WebSocket not connected', toolRuns: [] }]);
    }
  };

  const submitFeedback = async () => {
    if (!sessionId) return;
    try {
      const res = await fetch('/feedback/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          rating: feedbackRating,
          comment: feedbackComment
        })
      });
      if (res.ok) {
        setOpenFeedback(false);
        setFeedbackComment('');
      }
    } catch (e) {
      console.error("Feedback submit failed", e);
    }
  };

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    const models = modelsList[newProvider] || [];
    if (models.length > 0) {
      setModel(models[0]);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', width: '100%', background: 'transparent', overflow: 'hidden' }}>
      
      {/* Left Panel: Conversation History */}
      <Box sx={{
        width: 280,
        borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'rgba(15, 23, 42, 0.25)',
        p: 2,
        height: '100%',
        overflowY: 'hidden',
        flexShrink: 0
      }}>
        <Button
          variant="contained"
          fullWidth
          onClick={handleNewChat}
          sx={{
            mb: 3,
            background: 'linear-gradient(to right, #6366f1, #818cf8)',
            fontWeight: 600,
            py: 1.2
          }}
        >
          ➕ New Chat
        </Button>
        
        <Typography variant="caption" sx={{ color: 'grey.500', fontWeight: 600, mb: 1.5, letterSpacing: '0.05em', textTransform: 'uppercase', px: 0.5 }}>
          Recent Conversations
        </Typography>
        
        {/* Scrollable list of sessions */}
        <Box sx={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 1, pr: 0.5 }}>
          {sessions.length === 0 ? (
            <Typography variant="body2" sx={{ color: 'grey.600', textAlign: 'center', mt: 4, fontStyle: 'italic' }}>
              No history found
            </Typography>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === sessionId;
              return (
                <Box
                  key={sess.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 1.5,
                    borderRadius: 2,
                    cursor: 'pointer',
                    bgcolor: isActive ? 'rgba(99, 102, 241, 0.08)' : 'transparent',
                    border: isActive ? '1px solid rgba(99, 102, 241, 0.2)' : '1px solid transparent',
                    color: isActive ? '#818cf8' : 'grey.400',
                    '&:hover': {
                      bgcolor: isActive ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                      color: isActive ? '#818cf8' : '#fff'
                    },
                    transition: 'all 0.2s ease',
                    minHeight: 52
                  }}
                  onClick={() => handleSelectSession(sess.id)}
                >
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, overflow: 'hidden', flexGrow: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: isActive ? 600 : 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                      {sess.model ? `${sess.model} Chat` : 'New Conversation'}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'grey.600', fontSize: '10px' }}>
                      {sess.created_at ? new Date(sess.created_at).toLocaleString() : ''}
                    </Typography>
                  </Box>
                  
                  {/* Delete Button */}
                  <IconButton
                    size="small"
                    sx={{
                      color: 'grey.600',
                      '&:hover': { color: 'error.main' },
                      p: 0.5,
                      ml: 1
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSession(sess.id);
                    }}
                  >
                    <span style={{ fontSize: '12px' }}>🗑️</span>
                  </IconButton>
                </Box>
              );
            })
          )}
        </Box>
      </Box>

      {/* Right Column: Chat Dialog Area */}
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', flexGrow: 1, p: 4, overflow: 'hidden' }}>
        
        {/* Configuration Header */}
        <Paper className="glass-panel" sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center', mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>LLM Provider</InputLabel>
            <Select
              value={provider}
              label="LLM Provider"
              onChange={(e) => handleProviderChange(e.target.value)}
            >
              {Object.keys(modelsList).map(prov => (
                <MenuItem key={prov} value={prov}>
                  {prov.charAt(0).toUpperCase() + prov.slice(1)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Model Select</InputLabel>
            <Select
              value={model}
              label="Model Select"
              onChange={(e) => setModel(e.target.value)}
            >
              {(modelsList[provider] || []).map(m => (
                <MenuItem key={m} value={m}>{m}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ flexGrow: 1 }} />

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: wsStatus === 'Connected' ? 'success.main' : 'error.main',
              boxShadow: wsStatus === 'Connected' ? '0 0 8px #10b981' : '0 0 8px #ef4444'
            }} />
            <Typography variant="caption" sx={{ color: 'grey.400', fontWeight: 600 }}>
              {wsStatus}
            </Typography>
          </Box>
          
          {sessionId && (
            <IconButton size="small" color="primary" onClick={() => setOpenFeedback(true)}>
              <ThumbUpIcon fontSize="small" />
            </IconButton>
          )}
        </Paper>

        {/* Messages Window */}
        <Box sx={{
          flexGrow: 1,
          overflowY: 'auto',
          mb: 3,
          p: 3,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          borderRadius: 3,
          bgcolor: 'rgba(15, 23, 42, 0.4)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        }}>
          {messages.length === 0 && (
            <Box sx={{ m: 'auto', textAlign: 'center', color: 'grey.600' }}>
              <Typography variant="h5" sx={{ fontWeight: 600, mb: 1, color: 'grey.500' }}>
                Welcome to Chatbot Admin Pane
              </Typography>
              <Typography variant="body2">
                Start chatting below. The LLM can dynamically resolve tools and lookup context.
              </Typography>
            </Box>
          )}

          {messages.map((msg, index) => {
            const isUser = msg.sender === 'user';
            const isError = msg.sender === 'error';
            
            return (
              <Box
                key={index}
                sx={{
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '75%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 1
                }}
              >
                {/* Bot Tool Log Execution */}
                {!isUser && msg.toolRuns && msg.toolRuns.map((tr, trIdx) => (
                  <Paper
                    key={trIdx}
                    variant="outlined"
                    sx={{
                      p: 1.5,
                      border: '1px dashed rgba(99, 102, 241, 0.3)',
                      bgcolor: 'rgba(99, 102, 241, 0.02)',
                      borderRadius: 2,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 1
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CodeIcon sx={{ color: 'primary.main', fontSize: '16px' }} />
                      <Typography variant="caption" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                        🔧 Executing: {tr.name}({JSON.stringify(tr.params)})
                      </Typography>
                      {tr.status === 'running' && <CircularProgress size={12} />}
                    </Box>
                    {tr.result && (
                      <Box component="pre" sx={{
                        m: 0,
                        p: 1,
                        bgcolor: '#020617',
                        borderRadius: 1,
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        maxH: '120px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        color: 'grey.300'
                      }}>
                        {tr.result}
                      </Box>
                    )}
                  </Paper>
                ))}

                {/* Chat Bubble */}
                {(msg.text || isError) && (
                  <Paper
                    sx={{
                      p: 2,
                      borderRadius: 3,
                      borderBottomRightRadius: isUser ? 1 : 3,
                      borderBottomLeftRadius: !isUser ? 1 : 3,
                      bgcolor: isUser 
                        ? 'primary.main' 
                        : isError 
                          ? 'rgba(239, 68, 68, 0.15)' 
                          : 'background.paper',
                      color: isError ? 'error.light' : '#fff',
                      border: isUser ? 'none' : '1px solid rgba(255,255,255,0.06)',
                      boxShadow: isUser ? '0 4px 12px rgba(99, 102, 241, 0.25)' : 'none',
                      lineHeight: 1.5
                    }}
                  >
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {msg.text}
                    </Typography>
                  </Paper>
                )}
              </Box>
            );
          })}

          {thinking && (
            <Box sx={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 1, color: 'grey.500', px: 2 }}>
              <CircularProgress size={14} color="inherit" />
              <Typography variant="body2" className="thinking-pulse" sx={{ fontStyle: 'italic' }}>
                Thinking...
              </Typography>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input area */}
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Type a message or trigger tools..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => { if (e.key === 'Enter') handleSend(); }}
            autoComplete="off"
          />
          <Button
            variant="contained"
            endIcon={<SendIcon />}
            onClick={handleSend}
            disabled={wsStatus !== 'Connected' || !message.trim()}
            sx={{ minWidth: '120px' }}
          >
            Send
          </Button>
        </Box>

        {/* Feedback Dialog */}
        <Dialog open={openFeedback} onClose={() => setOpenFeedback(false)}>
          <DialogTitle sx={{ fontWeight: 600 }}>Submit Session Feedback</DialogTitle>
          <DialogContent dividers sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="body2">
              Rate this chat session's accuracy and performance:
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <Rating
                size="large"
                value={feedbackRating}
                onChange={(event, newValue) => {
                  setFeedbackRating(newValue);
                }}
              />
            </Box>
            <TextField
              multiline
              rows={3}
              label="Additional Comments (optional)"
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="Help us improve this model session..."
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenFeedback(false)}>Cancel</Button>
            <Button variant="contained" onClick={submitFeedback}>Submit</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Box>
  );
}
