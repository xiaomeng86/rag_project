import { BaseLayout } from '@/layout/base'
import { Outlet, useLocation } from 'react-router-dom'
import { RouterGuard } from './guard'

export function Layout() {
  const location = useLocation()
  return (
    <BaseLayout>
      <RouterGuard>
        <Outlet key={location.pathname} />
      </RouterGuard>
    </BaseLayout>
  )
}
