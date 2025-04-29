import axios from 'axios';

// Create an Axios instance (optional but good for scaling later)
const api = axios.create({
  baseURL: 'http://localhost:5000/api', // Adjust if your backend runs elsewhere
});

// API call to register a visitor
export const registerVisitor = (visitorData) => {
  return api.post('/visitor/register', visitorData);
};

// You can add more API calls here later (for Admin Dashboard etc.)
