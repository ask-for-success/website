import React from 'react';
import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="afs-footer">
      <div className="container">

        {/* MAIN FOOTER */}
        <div className="afs-footer-main">

          {/* LOGO */}
          
{/* FOOTER LOGO */}
<div className="afs-footer-brand">
  <Link to="/" className="afs-footer-brand-link">
    <img
      src="/assets/images/logos/logofooter.png"
      alt="Ask For Success logo"
      className="afs-footer-logo"
    />

    <h3 className="afs-footer-brand-title">
      Ask For Success
    </h3>

    <p className="afs-footer-brand-tagline">
      Where your success story begins.
    </p>
  </Link>
</div>


          {/* NAVIGATION */}
          <div className="afs-footer-column">
            <h3>Navigation</h3>

            <Link to="/">Home</Link>
            <Link to="/about">About</Link>
            <Link to="/gallery">Gallery</Link>
            <Link to="/events">Events</Link>
            <Link to="/news">Blog/News</Link>
          </div>

          {/* GET INVOLVED */}
          <div className="afs-footer-column">
            <h3>Get Involved</h3>

            <Link to="/get-involved">Volunteer</Link>
            <Link to="/get-involved">Donate</Link>
            <Link to="/get-involved">Partner</Link>
          </div>

          {/* CONTACT */}
          <div className="afs-footer-column afs-footer-contact">
            <h3>Contact</h3>

            <a href="mailto:askforsuccess@gmail.com">
              Email: askforsuccess@gmail.com
            </a>

            <a href="tel:+212600000000">
              Phone: +212 6 00 00 00 00
            </a>

            <p>Casablanca, Morocco</p>
          </div>

        </div>

        {/* FOOTER BOTTOM */}
        <div className="afs-footer-bottom">

          <p>
            © 2026 Ask For Success (AFS). All rights reserved.
          </p>

          <div className="afs-footer-social">
            <span>Follow us</span>

            <div className="afs-social-icons">

              {/* TIKTOK */}
              <a
                href="https://www.tiktok.com/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="TikTok"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M16.7 2c.2 2.2 1.5 3.6 3.7 3.8v3.8a8.2 8.2 0 0 1-3.7-1v6.5a6.4 6.4 0 1 1-6.4-6.4h.7v3.9a2.5 2.5 0 1 0 1.8 2.4V2h3.9Z" />
                </svg>
              </a>

              {/* YOUTUBE */}
              <a
                href="https://www.youtube.com/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="YouTube"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <rect
                    x="2"
                    y="5"
                    width="20"
                    height="14"
                    rx="4"
                  />
                  <path d="m10 9 5 3-5 3V9Z" />
                </svg>
              </a>

              {/* INSTAGRAM */}
              <a
                href="https://www.instagram.com/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <rect
                    x="2"
                    y="2"
                    width="20"
                    height="20"
                    rx="5"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="4"
                  />
                  <circle
                    cx="17.5"
                    cy="6.5"
                    r="1"
                    fill="currentColor"
                    stroke="none"
                  />
                </svg>
              </a>

              {/* LINKEDIN */}
              <a
                href="https://www.linkedin.com/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M20.45 2H3.55C2.69 2 2 2.68 2 3.52v16.96c0 .84.69 1.52 1.55 1.52h16.9c.86 0 1.55-.68 1.55-1.52V3.52c0-.84-.69-1.52-1.55-1.52ZM7.93 18.75H4.98V9.2h2.95v9.55ZM6.45 7.9a1.71 1.71 0 1 1 0-3.42 1.71 1.71 0 0 1 0 3.42Zm12.3 10.85H15.8V14.1c0-1.11-.02-2.54-1.55-2.54-1.55 0-1.79 1.21-1.79 2.46v4.73H9.51V9.2h2.83v1.3h.04c.39-.74 1.36-1.52 2.8-1.52 3 0 3.57 1.97 3.57 4.53v5.24Z" />
                </svg>
              </a>

            </div>
          </div>
        </div>

      </div>
    </footer>
  );
}
