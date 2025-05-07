import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Container, Button } from '@mui/material';
import VisitorRegistration from './components/VisitorRegistration';
import AdminDashboard from './components/AdminDashboard';

const App = () => {
    return (
        <Router>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                        ParkSense
                    </Typography>
                    <Button color="inherit" component={Link} to="/">
                        Visitor Registration
                    </Button>
                    <Button color="inherit" component={Link} to="/admin">
                        Admin Dashboard
                    </Button>
                </Toolbar>
            </AppBar>

            <Container>
                <Routes>
                    <Route path="/" element={<VisitorRegistration />} />
                    <Route path="/admin" element={<AdminDashboard />} />
                </Routes>
            </Container>
        </Router>
    );
};

export default App;
