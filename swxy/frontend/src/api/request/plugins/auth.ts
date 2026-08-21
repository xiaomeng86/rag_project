import { router } from '@/router/routes'
import { userActions, userState } from '@/store/user'
import { ResponseError } from '../error'
import { IRequestPlugin } from './plugin'

const AUTH_ERROR_MAP = {
  401: '登录状态已失效，请重新登录',
}

const blackList = ['/auth/login']

export const authPlugin: IRequestPlugin = {
  install(instance) {
    instance.interceptors.request.use((config) => {
      const { token } = userState
      if (token && !config.headers['Authorization']) {
        config.headers['Authorization'] = `Bearer ${token}`
      }
      return config
    })

    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        const response = error.response
        if (!response) return Promise.reject(error)
        const url = response.config.url as string
        if (blackList.includes(url)) return Promise.reject(error)

        const code = response?.status
        const msg = response?.data?.message || response?.data?.detail

        let message: string
        switch (code) {
          case 401:
            // token 失效
            userActions.setToken('')
            router.navigate('/login')

            message =
              AUTH_ERROR_MAP[code as keyof typeof AUTH_ERROR_MAP] ||
              msg ||
              '请求发生错误'

            return Promise.reject(new ResponseError(message, response))
          case 461:
            // 知识库中没有文档
            message = '请先上传文档'
            router.navigate('/repository')

            return Promise.reject(new ResponseError(message, response))
          default:
            return Promise.reject(error)
        }
      },
    )
  },
}
