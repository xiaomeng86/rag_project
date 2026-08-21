import NotFound from '@/pages/404'
import Chat from '@/pages/chat'
import Index from '@/pages/index'
import Login from '@/pages/login'
import Repository from '@/pages/repository'
import { RouteObject, createBrowserRouter } from 'react-router-dom'
import { Layout } from './layout'

export type IRouteObject = {
  children?: IRouteObject[]
  name?: string
  auth?: boolean
  pure?: boolean
  meta?: any
} & Omit<RouteObject, 'children'>

export const routes: IRouteObject[] = [
  {
    path: '/',
    Component: Index,
  },
  {
    path: '/chat/:id',
    Component: Chat,
  },
  {
    path: '/repository',
    Component: Repository,
  },
]

export const router = createBrowserRouter(
  [
    helper({
      path: '/',
      Component: Layout,
      children: routes,
    }),
    helper({
      path: '/login',
      Component: Login,
      auth: false,
    }),
    helper({
      path: '404',
      Component: NotFound,
      pure: true,
    }),
    helper({
      path: '*',
      Component: NotFound,
    }),
  ],
  {
    basename: import.meta.env.BASE_URL,
  },
)

function helper(route: IRouteObject) {
  const _route = {
    ...route,
  }

  if (_route.children) {
    _route.children = _route.children.map((child: any) => helper(child))
  }

  if (_route.auth === undefined) {
    _route.auth = true
  }

  return _route as RouteObject
}
