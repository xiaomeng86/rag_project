import { Tag } from 'antd'
import Color from 'color'
import { useMemo } from 'react'

const map = {
  processing: {
    text: '解析中',
    color: '#E6A23C',
  },
  ready: {
    text: '已完成',
    color: '#409EFF',
  },
}

export function Status(props: { status: keyof typeof map }) {
  const { status } = props
  const { text, color } = useMemo(() => {
    return (
      map[status] ?? {
        color: '#999',
        text: status,
      }
    )
  }, [status])

  const backgroundColor = useMemo(() => {
    return new Color(color).alpha(0.1).toString()
  }, [color])

  const borderColor = useMemo(() => {
    return new Color(color).alpha(0.3).toString()
  }, [color])

  return (
    <Tag style={{ borderColor, color, backgroundColor }}>{text}</Tag>
  )
}
