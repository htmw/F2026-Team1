import "../styles/meta-list.css";

function MetaList({ items }) {
  return (
    <dl className="meta-list">
      {items.map((item) => (
        <div key={item.label} className="meta-list__item">
          <dt className="label-mono">{item.label}</dt>
          <dd className="body-md">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default MetaList;
