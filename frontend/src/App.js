import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminDashboard from './pages/AdminDashboard';
import VisitorForm from './pages/VisitorForm';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/" element={<VisitorForm />} />
      </Routes>
    </Router>
  );
}

export default App;
