import { Link, NavLink, useNavigate } from "react-router-dom";
import ThemeToggle from "./ThemeToggle.jsx";
import "../styles/navbar.css";
import logo from "../assets/images/logo.png";
import useAuth from "../hooks/useAuth.js";

function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function signout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <nav className="nav">
      <div className="nav-container">
        <div className="nav__left">
          <Link className="nav__logo-link" aria-label="DUAL home" to="/">
            <div className="nav__logo-container">
              <div className="nav__logo-img-container">
                <img src={logo} alt="logo" className="nav__logo-img" />
              </div>
              <div className="nav__logo-text-container">
                <p className="nav__logo-text--primary logo-wordmark">DUAL</p>
                <p className="nav__logo-text--secondary logo-descriptor">
                  OCULAR DISEASE SCREENER
                </p>
              </div>
            </div>
          </Link>

          <div className="vertical-line" role="presentation"></div>

          <ul className="nav__list">
            <li className="nav__list-item">
              <NavLink className="nav__link body-md" to="/upload">
                Upload
              </NavLink>
            </li>
            <li className="nav__list-item">
              <NavLink className="nav__link body-md" to="/history">
                History
              </NavLink>
            </li>
            <li className="nav__list-item">
              <NavLink className="nav__link body-md" to="/about">
                About
              </NavLink>
            </li>
          </ul>
        </div>
        <div className="nav__right">
          <ThemeToggle />
          <div className="user chip chip--neutral">
            <div className="user-status" role="presentation"></div>
            <p className="caption-md">{user?.name}</p>
          </div>

          <button onClick={signout} className="nav__btn--signout body-md">
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
