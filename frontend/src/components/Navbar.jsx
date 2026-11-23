import React from 'react';
import { Link, NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Home' },
  { to: '/about', label: 'About' },
  { to: '/get-involved', label: 'Get Involved' },
  { to: '/gallery', label: 'Gallery' },
  { to: '/events', label: 'Events' },
  { to: '/news', label: 'News' },
];

function revealFocusedLink({ currentTarget, target }) {
  if (currentTarget.scrollWidth > currentTarget.clientWidth) {
    target.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
}

export default function Navbar() {
  return (
    <header className="site-header">
      <nav className="navbar site-shell" aria-label="Main navigation">
        <Link className="brand" to="/" aria-label="AFS Home">
          <img
            src="/assets/images/logos/AFS logo.png"
            alt="Ask For Success"
            className="navbar-logo"
          />
        </Link>

        <div className="nav-links" onFocus={revealFocusedLink}>
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
            >
              {label}
            </NavLink>
          ))}
        </div>

        <div className="navbar-actions">
          <Link to="/get-involved#donate" className="donate-button">
            Donate
          </Link>
        </div>
      </nav>
    </header>
  );
}
