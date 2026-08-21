import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function register(
  params: {
    username: string
    password: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<{
    user_id: number
    username: string
    message: string
  }>(`/auth/register`, params, options)
}

export function login(
  params: {
    username: string
    password: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<{
    access_token: string
    token_type: string
  }>(`/auth/login`, params, options)
}
