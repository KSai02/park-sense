// import React from 'react';
// import VisitorForm from './pages/VisitorForm'; // Adjust if your path is different

// function App() {
//   return (
//     <div>
//       <h1>Welcome to ParkSense 🚗</h1>
//       <VisitorForm />
//     </div>
//   );
// }

// export default App;
// import React from 'react';
// import VisitorForm from './pages/VisitorForm';  // Import your form page

// function App() {
//   return (
//     <div>
//       <h1 style={{ textAlign: 'center', marginTop: '20px' }}>Welcome to ParkSense 🚗</h1>
//       <VisitorForm />
//     </div>
//   );
// }

// export default App;
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import AdminDashboard from './pages/AdminDashboard'; // Admin Page Component
import VisitorForm from './pages/VisitorForm'; // Visitor Form Page Component

function App() {
  return (
    <Router>
      <Switch>
        <Route path="/admin" component={AdminDashboard} />
        <Route path="/" component={VisitorForm} />
      </Switch>
    </Router>
  );
}

export default App;
