import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const runPipeline     = () => api.get('/pipeline/run')
export const getMeters       = () => api.get('/pipeline/meters')
export const refreshPipeline = async () => {
  await api.get('/pipeline/refresh')
}

export default api