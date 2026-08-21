import IconFile from '@/assets/chat/file.svg'
import styles from './contracts.module.scss'

function ContractItem(props: { item: API.Document }) {
  const { item } = props

  return (
    <div className={styles['contracts__item']}>
      <img className={styles['icon']} src={IconFile} />
      <div className={styles['name']} title={item.document_name}>
        {item.document_name}
      </div>
    </div>
  )
}

export default function Contracts(props: { list: API.Document[] }) {
  const { list } = props

  return (
    <div className={styles['contracts']}>
      <div className={styles['contracts__title']}>本轮证据文档</div>

      <div className={styles['contracts__list']}>
        {list.length ? (
          list.map((item) => (
            <ContractItem key={item.document_id} item={item} />
          ))
        ) : (
          <div className={styles['contracts__empty']}>发送问题后显示来源</div>
        )}
      </div>
    </div>
  )
}
