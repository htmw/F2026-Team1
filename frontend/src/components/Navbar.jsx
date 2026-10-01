import { Link } from "react-router-dom";
import "../styles/global.css";
import "../styles/navbar.css";
import logo from "../assets/images/logo.png";

function Navbar() {
  function signout() {
    return;
  }

  return (
    <nav className="nav">
      <div className="nav-container">
        <div className="nav__left">
          <Link className="nav__logo-link" to="/">
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
              <Link className="nav__link body-md" to="/upload">
                Upload
              </Link>
            </li>
            <li className="nav__list-item">
              <Link className="nav__link body-md" to="/history">
                History
              </Link>
            </li>
            <li className="nav__list-item">
              <Link className="nav__link body-md" to="/about">
                About
              </Link>
            </li>
          </ul>
        </div>
        <div className="nav__right">
          <div className="user chip chip--neutral">
            <div className="user-status" role="presentation"></div>
            <p className="caption-md">Dr. Emily Geller</p>
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
