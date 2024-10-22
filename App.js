import React, { useState, useEffect } from 'react';
import './App.css';
import { AppBar, Toolbar, Typography, TextField, Button, Box, Container } from '@mui/material';
import axios from 'axios';
import { BrowserRouter as Router, Route, Routes, useNavigate } from 'react-router-dom';
import io from 'socket.io-client';

import ResultsPage from './results'; // Updated to ResultsPage for clarity

const socket = io('http://localhost:3001');

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [output, setOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    socket.on('output', (data) => {
      setOutput((prevOutput) => prevOutput + data);
    });

    return () => {
      socket.off('output');
    };
  }, []);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    setIsLoading(true);

    const data = {
      searchTerm: searchTerm.trim(), 
    };

    axios.post('http://localhost:3001/search', data)
      .then(response => {
        if (response.data.message === 'Processing complete') {
          setIsLoading(false);
          navigate('/results', { state: { searchTerm: searchTerm.trim() } });
        }
      })
      .catch(error => {
        console.error('Error:', error);
        setIsLoading(false);
      });
  };

  return (
    <div className="App">
      <AppBar position="static">
        <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <img src="/Baylor.png" alt="Baylor Logo" style={{ height: '90px', marginLeft: '2px' }} />
          </Box>
        </Toolbar>
      </AppBar>
      <Container>
        <header className="App-header" style={{ backgroundColor: 'transparent' }}>
          <Box component="form" onSubmit={handleSearchSubmit} sx={{ display: 'flex', alignItems: 'center', width: '100%', mt: 2 }}>
            <TextField
              fullWidth
              value={searchTerm}
              onChange={handleSearchChange}
              placeholder="Search..."
              variant="outlined"
              size="small"
              sx={{ backgroundColor: 'white', borderRadius: 2 }}
            />
            <Button type="submit" variant="contained" color="primary" sx={{ ml: 2 }} disabled={isLoading}>
              {isLoading ? 'Processing...' : 'Search'}
            </Button>
          </Box>
          <Box sx={{ mt: 4, p: 2, border: '1px solid grey', borderRadius: 2, width: '100%', height: '400px', overflowY: 'scroll', backgroundColor: '#f5f5f5' }}>
            <Typography variant="body1" style={{ whiteSpace: 'pre-wrap', color: 'black' }}>
              {output}
            </Typography>
          </Box>
        </header>
      </Container>
    </div>
  );
}

function MainApp() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </Router>
  );
}

export default MainApp;