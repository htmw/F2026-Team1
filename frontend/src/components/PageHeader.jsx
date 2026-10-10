import "../styles/page-header.css";

function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && (
          <p className="page-header__eyebrow label-mono">{eyebrow}</p>
        )}
        <h1 className="h1">{title}</h1>
        {subtitle && (
          <p className="page-header__subtitle body-rg">{subtitle}</p>
        )}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

export default PageHeader;
