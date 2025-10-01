// frontend/src/api.js
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_URL,
});

export default apiClient;