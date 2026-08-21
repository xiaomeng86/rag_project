import IconCompleted from '@/assets/chat/completed.svg'
import { RightOutlined } from '@ant-design/icons'
import styles from './select-file.module.scss'

export function EvidenceSearching() {
  return (
    <div className={styles['select-file-searching']}>
      <div className={styles['icon']}></div>
      <div className={styles['title']}>正在搜索知识库</div>
    </div>
  )
}
export function EvidenceComplete(props: {
  contractsLength: number
  citationsLength: number
  onClick?: () => void
}) {
  const { contractsLength, citationsLength, onClick } = props

  return (
    <div className={styles['select-file-complete']} onClick={onClick}>
      <img className={styles['icon']} src={IconCompleted} />
      <div className={styles['title']}>参考</div>
      <div className={styles['desc']}>
        {citationsLength ?? 0}个引文 来自{contractsLength ?? 0}个文件
      </div>
      <RightOutlined className={styles['arrow']} />
    </div>
  )
}
