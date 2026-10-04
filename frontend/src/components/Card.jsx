import "../styles/card.css";

function Card({ title, aside, children }) {
  return (
    <section className="card">
      {(title || aside) && (
        <header className="card__header">
          {title && <h2 className="card__title label-mono">{title}</h2>}
          {aside && <p className="card__aside mono-meta">{aside}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

export default Card;
