import React from 'react';
import { Link, NavLink } from 'react-router-dom';

const links = [
  { to: '/about', label: 'About' },
  { to: '/get-involved', label: 'Get involved' },
  { to: '/gallery', label: 'Gallery' },
  { to: '/events', label: 'Events' },
  { to: '/news', label: 'Blog/News' },
];

export default function Navbar() {
  return (
    <header className="site-header">
      <nav className="navbar container" aria-label="Main navigation">

        {/* LOGO */}
        <Link className="brand" to="/" aria-label="AFS Home">
          <img
            src="/assets/images/logos/AFS logo.png"
            alt="Ask For Success"
            className="navbar-logo"
          />
        </Link>

        {/* CENTER LINKS */}
        <div className="nav-links">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>

        {/* RIGHT ACTIONS */}
        <div className="navbar-actions">
          <Link to="/get-involved" className="donate-button">
            Donate
          </Link>
        </div>

      </nav>
    </header>
  );
}
