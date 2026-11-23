import React from 'react';
import { Link } from 'react-router-dom';

const socialIcons = ['tiktok.svg', 'youtube.svg', 'instagram.svg', 'linkedin.svg'];

export default function Footer() {
  return (
    <footer className="afs-footer">
      <div className="site-shell">
        <div className="afs-footer-main">
          <div className="afs-footer-brand">
            <Link to="/" className="afs-footer-brand-link">
              <span className="afs-footer-logo">
                <img src="/assets/images/logos/afs-footer-v2.png" alt="" />
              </span>
              <span className="afs-footer-brand-title">Ask For Success</span>
              <span className="afs-footer-brand-tagline">
                Where your success story begins.
              </span>
            </Link>

            <div className="afs-footer-cta">
              <p>Ready to make a difference?</p>
              <Link to="/get-involved">
                <span>Get involved</span>
                <img src="/assets/icons/shared/footer-arrow.svg" alt="" />
              </Link>
            </div>
          </div>

          <div className="afs-footer-column">
            <h3>Navigation</h3>
            <div className="afs-footer-links">
              <Link to="/">Home</Link>
              <Link to="/about">About</Link>
              <Link to="/gallery">Gallery</Link>
              <Link to="/events">Events</Link>
              <Link to="/news">News</Link>
            </div>
          </div>

          <div className="afs-footer-column">
            <h3>Get Involved</h3>
            <div className="afs-footer-links">
              <Link to="/get-involved#volunteer">Volunteer</Link>
              <Link to="/get-involved#donate">Donate</Link>
              <Link to="/get-involved#partner">Partner</Link>
            </div>
          </div>

          <div className="afs-footer-column afs-footer-contact">
            <h3>Contact</h3>
            <div className="afs-footer-links">
              <a href="mailto:askforsuccess@gmail.com">
                Email: askforsuccess@gmail.com
              </a>
              <p>Phone unavailable</p>
              <p>Casablanca, Morocco</p>
            </div>
          </div>
        </div>

        <div className="afs-footer-bottom">
          <p>© 2026 Ask For Success (AFS). All rights reserved.</p>
          <div className="afs-footer-social">
            <p>Social links unavailable</p>
            <div className="afs-social-icons" aria-hidden="true">
              {socialIcons.map((icon) => (
                <img key={icon} src={`/assets/icons/shared/${icon}`} alt="" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
