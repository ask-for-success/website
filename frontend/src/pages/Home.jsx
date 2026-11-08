import React from 'react';
import { Link } from 'react-router-dom';
import StatsSection from '../components/StatsSection.jsx';
import {
  GraduationCap,
  Star,
  UsersRound,
  ChartNoAxesColumnIncreasing,
  ArrowRight,
  HandHeart,
  Hand,
  Handshake,
  MapPin,
} from 'lucide-react';

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="container hero-layout">
          {/* LEFT SIDE: TEXT */}
          <div className="hero-text">
            <h1>
              Where your <br />
              success story <br />
              <span>begins</span>
            </h1>

            <p className="hero-description">
              Empowering Morocco’s youth through mentorship, education,
              leadership, and community.
            </p>

            <div className="hero-actions">
              <Link to="/get-involved" className="hero-donate">
                Donate
              </Link>

              <Link to="/get-involved" className="hero-partner">
                Become a partner
                <span className="hero-arrow" aria-hidden="true">
                  ➜
                </span>
              </Link>
            </div>
          </div>

          {/* RIGHT SIDE: IMAGE */}
          <div className="hero-visual">
            <div className="hero-purple-shape"></div>

            <img
              src="/assets/images/home/hero.jpg"
              alt="Young students participating in an AFS community initiative"
              className="hero-photo"
            />
          </div>
        </div>
      </section>

      {/* ABOUT OUR ASSOCIATION */}
      <section className="home-about">
        <div className="container home-about-layout">
          {/* LEFT: IMAGE */}
          <div className="home-about-image">
            <img
              src="/assets/images/home/home about.jpg"
              alt="AFS volunteer representing the association"
              loading="lazy"
            />
          </div>

          {/* RIGHT: CONTENT */}
          <div className="home-about-content">
            <h2>About Our Association</h2>

            <p className="home-about-description">
              <strong>Ask For Success</strong> is a Moroccan non-profit
              dedicated to opening doors for students and young people. Through
              events, mentorship, and community support, we help turn
              opportunity into real success stories.
            </p>

            {/* FEATURE BADGES */}
            <div className="home-about-features">
              <div className="home-about-feature">
                <span className="home-about-feature-icon">
                  <GraduationCap size={19} />
                </span>
                <span>Education &amp; mentorship</span>
              </div>

              <div className="home-about-feature">
                <span className="home-about-feature-icon">
                  <Star size={19} />
                </span>
                <span>Opportunity access</span>
              </div>

              <div className="home-about-feature">
                <span className="home-about-feature-icon">
                  <UsersRound size={19} />
                </span>
                <span>Community events</span>
              </div>

              <div className="home-about-feature">
                <span className="home-about-feature-icon">
                  <ChartNoAxesColumnIncreasing size={19} />
                </span>
                <span>Measurable impact</span>
              </div>
            </div>

            {/* BUTTON */}
            <Link to="/about" className="home-about-button">
              Learn More About Us
              <span className="home-about-button-arrow" aria-hidden="true">
                <ArrowRight size={17} />
              </span>
            </Link>
          </div>
        </div>
      </section>

      <StatsSection />

      {/* WAYS TO GET INVOLVED */}
      <section className="home-involved">
        <div className="container">
          {/* SECTION HEADER */}
          <div className="home-involved-header">
            <div>
              <h2>Ways to get involved</h2>
              <p className="home-involved-subtitle">
                Three ways to make an impact.
              </p>
            </div>

            <p className="home-involved-intro">
              Every contribution—whether your time, professional expertise, or
              financial patronage—directly enriches a young Moroccan's future.
            </p>
          </div>

          {/* THREE CARDS */}
          <div className="home-involved-grid">
            {/* DONATE */}
            <article className="home-involved-card">
              <div className="home-involved-icon">
                <HandHeart size={23} />
              </div>

              <h3>Donate</h3>
              <p>
                Fuel student workshops, hardware tech kits, and rural youth
                outreach programs with tax-deductible contributions.
              </p>

              <Link to="/get-involved" className="home-involved-link">
                Learn more <ArrowRight size={17} />
              </Link>
            </article>

            {/* VOLUNTEER */}
            <article className="home-involved-card">
              <div className="home-involved-icon">
                <Hand size={23} />
              </div>

              <h3>Volunteer</h3>
              <p>
                Offer your mentorship or operational time to empower Moroccan
                students across regional chapters and workshops.
              </p>

              <Link to="/get-involved" className="home-involved-link">
                Learn more <ArrowRight size={17} />
              </Link>
            </article>

            {/* PARTNER */}
            <article className="home-involved-card">
              <div className="home-involved-icon">
                <Handshake size={23} />
              </div>

              <h3>Partner</h3>
              <p>
                Collaborate as an educational institution, international NGO, or
                corporate sponsor for long-term career ecosystems.
              </p>

              <Link to="/get-involved" className="home-involved-link">
                Learn more <ArrowRight size={17} />
              </Link>
            </article>
          </div>
        </div>
      </section>

      {/* UPCOMING EVENTS */}
      <section className="home-events">
        <div className="container">
          <div className="home-events-header">
            <div>
              <h2>Upcoming Events</h2>
              <p>Three ways to make an impact.</p>
            </div>

            <Link to="/events" className="home-events-view-all">
              View All events
              <ArrowRight size={18} />
            </Link>
          </div>

          <div className="home-events-grid">
            {/* FEATURED EVENT */}
            <article className="home-event-card home-event-featured">
              <div className="home-event-image">
                <img
                  src="/assets/images/home/upcoming.jpg"
                  alt="AFS volunteers participating in a youth community event"
                  loading="lazy"
                />

                <span className="home-event-location">
                  <MapPin size={15} />
                  Casablanca, Ain chok
                </span>
              </div>

              <div className="home-event-content">
                <time className="home-event-date" dateTime="2026-10-31">
                  31 OCT 2026
                </time>

                <h3>Next Morocco Youth Summit 2026</h3>

                <p>
                  Join over 600 student delegates, startup founders, and mentors
                  for two days of collaborative innovation, keynote addresses,
                  and national hackathon presentations.
                </p>

                <Link to="/events" className="home-event-button">
                  Register now
                  <span className="home-event-arrow">
                    <ArrowRight size={15} />
                  </span>
                </Link>
              </div>
            </article>

            {/* RIGHT COLUMN */}
            <div className="home-events-side">
              {[1, 2].map((item) => (
                <article
                  className="home-event-card home-event-small"
                  key={item}
                >
                  <time className="home-event-date" dateTime="2026-10-31">
                    31 OCT 2026
                  </time>

                  <h3>Next Morocco Youth Summit 2026</h3>

                  <p>
                    Join over 600 student delegates, startup founders, and
                    mentors for two days of collaborative innovation, keynote
                    addresses, and national hackathon presentations.
                  </p>

                  <Link to="/events" className="home-event-button">
                    Register now
                    <span className="home-event-arrow">
                      <ArrowRight size={15} />
                    </span>
                  </Link>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
