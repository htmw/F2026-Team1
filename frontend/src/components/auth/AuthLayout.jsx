import Card from "../Card.jsx";
import ThemeToggle from "../ThemeToggle.jsx";
import logo from "../../assets/images/logo.png";
import "../../styles/auth/auth-layout.css";

function AuthLayout({ title, subtitle, footer, children }) {
  return (
    <main className="auth">
      <div className="auth__theme">
        <ThemeToggle />
      </div>

      <div className="auth__panel">
        <div className="auth__brand">
          <img src={logo} alt="" className="auth__logo" />
          <div>
            <p className="auth__wordmark logo-wordmark">DUAL</p>
            <p className="auth__descriptor logo-descriptor">
              OCULAR DISEASE SCREENER
            </p>
          </div>
        </div>

        <Card>
          <div className="auth__body">
            <header className="auth__header">
              <h1 className="h1">{title}</h1>
              {subtitle && <p className="auth__subtitle body-rg">{subtitle}</p>}
            </header>
            {children}
          </div>
        </Card>

        {footer && <p className="auth__footer body-rg">{footer}</p>}
        <p className="auth__note caption-rg">
          Triage, not diagnosis. For use by clinic staff only.
        </p>
      </div>
    </main>
  );
}

export default AuthLayout;
