import { createRequest } from './request'

export const request = createRequest({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  loading: true,
  errorToast: true,
  cancelRepeat: true,
})
