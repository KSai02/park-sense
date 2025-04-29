import axios from 'axios';

const API = axios.create({ baseURL: 'http://localhost:5000/api' });

export const registerVisitor = (visitorData) => API.post('/visitor/register', visitorData);
export const fetchSlots = () => API.get('/admin/slots');
export const fetchSlotDetails = (id) => API.get(`/admin/slot/${id}`);
