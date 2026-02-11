import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (userData) => api.post('/auth/register', userData),
  login: (credentials) => api.post('/auth/login', credentials),
  me: () => api.get('/auth/me'),
};

// Projects API
export const projectsAPI = {
  getAll: () => api.get('/projects'),
  getOne: (id) => api.get(`/projects/${id}`),
  create: (projectData) => api.post('/projects', projectData),
  delete: (id) => api.delete(`/projects/${id}`),
  getStatistics: (id) => api.get(`/projects/${id}/statistics`),
  getGraph: (id, limit = 50) => api.get(`/projects/${id}/graph`, { params: { limit } }),
};

// Documents API
export const documentsAPI = {
  getAll: (projectId) => api.get(`/projects/${projectId}/documents`),
  upload: (projectId, file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${projectId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
  },
  delete: (projectId, documentId) => 
    api.delete(`/projects/${projectId}/documents/${documentId}`),
};

// Query API
export const queryAPI = {
  ask: (queryData) => api.post('/query', queryData),
};

export default api;
